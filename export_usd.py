import importlib
import os
import sys

import maya.cmds as cmds
import maya.mel as mel
from playsound import playsound

# import p4 utils
project_root = os.getenv("film_root")
if not project_root:
    raise Exception("environment variable: film_root not found")
python_utils_path = os.path.join(project_root, "pipeline/packages/2AM/python_utils")
p4_utils_path = os.path.join(python_utils_path, "p4utils.py")
if not os.path.exists(p4_utils_path):
    raise Exception(f"can't find p4utils.py file in: {p4_utils_path}")
sys.path.append(python_utils_path)

import p4utils

importlib.reload(p4utils)


render_geo_whitelist = ["render"]
# render_geo_whitelist = ["Render", "Muscles", "Fat"]


def main():
    load_plugins()
    shot_num = os.getenv("SHOT_NUM")
    start_frame = cmds.playbackOptions(q=True, animationStartTime=True)
    end_frame = cmds.playbackOptions(q=True, animationEndTime=True)
    frame_range = (start_frame, end_frame)
    # frame_range = (1001, 1001)
    frame_step = 1

    change_num = p4utils.make_change("animation tool test")
    export_anim(frame_range, frame_step, change_num)


def get_characters():
    groups = cmds.ls("geo", long=True)
    print("found groups", groups)

    matching_groups = []
    characters = []

    for grp in groups:
        print("grp:", grp)
        parent = cmds.listRelatives(grp, parent=True, fullPath=True)

        if parent:
            parent_name = parent[0]

            if parent_name.endswith("_anim"):
                characters.append(parent_name[1:-5])
                matching_groups.append(grp)
    print("matching groups", matching_groups)
    print("characters:", characters)

    return (characters, matching_groups)


def load_plugins():
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        cmds.loadPlugin("mayaUsdPlugin")


def export_anim(frame_range, frame_step, change_num):
    # start_frame = frame_range[0]
    # end_frame = frame_range[1]
    # frame_step = frame_range[2]

    #    if not cmds.pluginInfo("AbcExport", query=True, loaded=True):
    #        cmds.loadPlugin("AbcExport")

    characters, matching_groups = get_characters()

    for i, character in enumerate(characters):
        group_name = matching_groups[i]
        children = cmds.listRelatives(group_name, children=True)
        filtered_children = [
            child for child in children if child in render_geo_whitelist
        ]
        if len(filtered_children) == 0:
            print(f"no groups match the whitelist: {render_geo_whitelist}")
            return

        print("filtered_children", filtered_children)
        print("children:", children)
        print(character, group_name)

        project_root = os.getenv("film_root")
        shot_num = os.getenv("SHOT_NUM")
        if not project_root or not shot_num:
            raise Exception("environment variables 'file_root' or 'SHOT_NUM' not set")
        export_file_path = f"{project_root}/usd/shots/SH{shot_num.zfill(4)}/scene_layers/anims/{character}.usd"
        print("EXPORT FILE PATH", export_file_path)
        export_file_already_exists = os.path.exists(export_file_path)
        export_file_p4_info = None
        if export_file_already_exists:
            print("FILE ALREADY EXISTS")
            file_info = p4utils.get_file_info(export_file_path)[0]
            print("FILE INFO", file_info)
            export_file_p4_info = file_info
            if file_info["status"] != "unopened":
                p4utils.edit(export_file_path, change_num=change_num)

        export_dirname = os.path.dirname(export_file_path)

        if not os.path.exists(export_dirname):
            print(f"{export_dirname} does not exist. Making path")
            os.makedirs(export_dirname)

        cmds.select(f"{group_name}|render")
        cmds.mayaUSDExport(
            file=export_file_path,
            selection=True,
            defaultMeshScheme="none",
            exportVisibility=False,
            exportUVs=False,
            exportMaterialCollections=False,
            shadingMode="none",
            frameRange=frame_range,
            frameStride=frame_step,
        )

        if (
            not export_file_already_exists
            or export_file_p4_info["status"] == "unopened"
        ):
            p4utils.add(export_file_path, change_num=change_num)

        # End the Maya session
        print("finished exporting file:", export_file_path)
    print("exported all characters")
    print("submitting to perforce...")
    p4utils.submit(change_num)
    print("finished submitting to perforce")

    finished_audio_path = os.path.join(
        project_root, "pipeline/elements/sounds/export_complete.mp3"
    )
    finished_audio_path = os.path.normpath(finished_audio_path)
    if os.path.exists(finished_audio_path):
        playsound(finished_audio_path)
    cmds.confirmDialog(message="Export Finished", title="Export Finished")


if __name__ == "__main__":
    main()
