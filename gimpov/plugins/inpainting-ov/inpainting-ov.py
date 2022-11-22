#!/usr/bin/env python3
# coding: utf-8
"""
Performs inpainting on a given image with another mask layer.
"""
import gi
gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gimp, GimpUi, GObject, GLib, Gio, Gtk
import gettext
import subprocess
import pickle
import os
import sys
sys.path.extend([os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")])
from plugin_utils import *

_ = gettext.gettext
image_paths = {
    "logo": os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "images", "plugin_logo.png"
    ),
    "error": os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "images", "error_icon.png"
    ),
}
#model_dict = {"Places2": "places2", "CelebA": "celeba", "Paris-StreetView": "psv"}


class StringEnum:
    """
    Helper class for when you want to use strings as keys of an enum. The values would be
    user facing strings that might undergo translation.

    The constructor accepts an even amount of arguments. Each pair of arguments
    is a key/value pair.
    """

    def __init__(self, *args):
        self.keys = []
        self.values = []

        for i in range(len(args) // 2):
            self.keys.append(args[i * 2])
            self.values.append(args[i * 2 + 1])

    def get_tree_model(self):
        """Get a tree model that can be used in GTK widgets."""
        tree_model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        for i in range(len(self.keys)):
            tree_model.append([self.keys[i], self.values[i]])
        return tree_model

    def __getattr__(self, name):
        """Implements access to the key. For example, if you provided a key "red", then you could access it by
        referring to
           my_enum.red
        It may seem silly as "my_enum.red" is longer to write then just "red",
        but this provides verification that the key is indeed inside enum."""
        key = name.replace("_", " ")
        if key in self.keys:
            return key
        raise AttributeError("No such key string " + key)



device_name_enum = StringEnum(
    "CPU",
    _("CPU"),
    "GPU",
    _("GPU"),
)


def inpainting(
    procedure,
    image,
    n_drawables,
    drawables,
    device_name,
    progress_bar,
    config_path_output,
):
    # Save inference parameters and layers
    weight_path = config_path_output["weight_path"]
    python_path = config_path_output["python_path"]
    plugin_path = config_path_output["plugin_path"]

    Gimp.context_push()
    image.undo_group_start()

    for index, drawable in enumerate(drawables):
        save_image(image, [drawable], os.path.join(weight_path,  "..", "cache" + str(index) + ".png"))

    with open(os.path.join(weight_path, "..", "gimp_ov_run.pkl"), "wb") as file:
        pickle.dump(
            {
                "device_name": device_name,
                "n_drawables": n_drawables,
                "inference_status": "started",
            },
            file,
        )

    # Run inference and load as layer
    subprocess.call([python_path, plugin_path])
    with open(os.path.join(weight_path, "..", "gimp_ov_run.pkl"), "rb") as file:
        data_output = pickle.load(file)
    image.undo_group_end()
    Gimp.context_pop()
    if data_output["inference_status"] == "success":
        result = Gimp.file_load(
            Gimp.RunMode.NONINTERACTIVE,
            Gio.file_new_for_path(os.path.join(weight_path, "..", "cache.png")),
        )
        result_layer = result.get_active_layer()
        copy = Gimp.Layer.new_from_drawable(result_layer, image)
        copy.set_name("OV InPainting")
        copy.set_mode(Gimp.LayerMode.NORMAL_LEGACY)  # DIFFERENCE_LEGACY
        image.insert_layer(copy, None, -1)

        # Remove temporary layers that were saved
        my_dir = os.path.join(weight_path, "..")
        for f_name in os.listdir(my_dir):
            if f_name.startswith("cache"):
                os.remove(os.path.join(my_dir, f_name))

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    else:
        show_dialog(
            "Inference not successful. See error_log.txt in GIMP-OV folder.",
            "Error !",
            "error",
            image_paths
        )
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


def run(procedure, run_mode, image, n_drawables, layer, args, data):
    device_name = args.index(0)

    if run_mode == Gimp.RunMode.INTERACTIVE:
        # Get all paths
        config_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "..", "tools"
        )
        with open(os.path.join(config_path, "gimp_ov_config.pkl"), "rb") as file:
            config_path_output = pickle.load(file)
        python_path = config_path_output["python_path"]
        config_path_output["plugin_path"] = os.path.join(config_path, "inpainting-ov.py")

        config = procedure.create_config()
        config.begin_run(image, run_mode, args)

        GimpUi.init("inpainting-ov.py")
        use_header_bar = Gtk.Settings.get_default().get_property(
            "gtk-dialogs-use-header"
        )

        # Check number of selected layers
        if n_drawables > 2:
            show_dialog(
                "Please select only image layer and mask layer.", "Error !", "error",image_paths
            )
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
        elif n_drawables == 2:
            n_drawables_text = _("Mask Selected | ")

        # Create UI
        dialog = GimpUi.Dialog(use_header_bar=use_header_bar, title=_("OV InPainting..."))
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("_Help", Gtk.ResponseType.APPLY)
        dialog.add_button("_Run Inference", Gtk.ResponseType.OK)

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, homogeneous=False, spacing=10
        )
        dialog.get_content_area().add(vbox)
        vbox.show()

        # Create grid to set all the properties inside.
        grid = Gtk.Grid()
        grid.set_column_homogeneous(False)
        grid.set_border_width(10)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        vbox.add(grid)
        grid.show()


        # Device Name parameter
        label = Gtk.Label.new_with_mnemonic(_("_Device Name"))
        grid.attach(label, 0, 0, 1, 1)
        label.show()
        combo = GimpUi.prop_string_combo_box_new(
            config, "device_name", device_name_enum.get_tree_model(), 0, 1
        )
        grid.attach(combo, 1, 0, 1, 1)
        combo.show()

        # Show Logo
        logo = Gtk.Image.new_from_file(image_paths["logo"])
        # grid.attach(logo, 0, 0, 1, 1)
        vbox.pack_start(logo, False, False, 1)
        logo.show()

        # Show License
        license_text = _("PLUGIN LICENSE : Apache-2.0")
        label = Gtk.Label(label=license_text)
        # grid.attach(label, 1, 1, 1, 1)
        vbox.pack_start(label, False, False, 1)
        label.show()

       

        progress_bar = Gtk.ProgressBar()
        vbox.add(progress_bar)
        progress_bar.show()

 


        # Wait for user to click
        dialog.show()
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                device_name = config.get_property("device_name")
                #model_name = config.get_property("model_name")
                result = inpainting(
                    procedure,
                    image,
                    n_drawables,
                    layer,
                    device_name,     
                    progress_bar,
                    config_path_output,
                )
                # If the execution was successful, save parameters so they will be restored next time we show dialog.
                if result.index(0) == Gimp.PDBStatusType.SUCCESS and config is not None:
                    config.end_run(Gimp.PDBStatusType.SUCCESS)
                return result
            elif response == Gtk.ResponseType.APPLY:
                url = "https://kritiksoman.github.io/GIMP-ML-Docs/docs-page.html#item-7-1"
                Gio.app_info_launch_default_for_uri(url, None)
                continue
            else:
                dialog.destroy()
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL, GLib.Error()
                )


class InPainting(Gimp.PlugIn):
    ## Parameters ##
    __gproperties__ = {
        "device_name": (
            str,
            _("Device Name"),
            "Device Name: 'CPU', 'GPU'",
            "CPU",
            GObject.ParamFlags.READWRITE,
        ),
    }

    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        self.set_translation_domain(
            "gimp30-python", Gio.file_new_for_path(Gimp.locale_directory())
        )
        return ["inpainting-ov"]

    def do_create_procedure(self, name):
        procedure = None
        if name == "inpainting-ov":
            procedure = Gimp.ImageProcedure.new(
                self, name, Gimp.PDBProcType.PLUGIN, run, None
            )
            procedure.set_image_types("*")
            procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLES)
            procedure.set_documentation(
                N_("Performs inpainting on a given image with another mask layer."),
                globals()[
                    "__doc__"
                ],  # This includes the docstring, on the top of the file
                name,
            )
            procedure.set_menu_label(N_("OV InPainting..."))
            procedure.set_attribution("Arisha Kumar", "GIMP-OV", "2022")
            procedure.add_menu_path("<Image>/Layer/GIMP-OV/")
            procedure.add_argument_from_property(self, "device_name")
        return procedure


Gimp.main(InPainting.__gtype__, sys.argv)
