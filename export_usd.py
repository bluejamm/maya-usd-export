import importlib
import os
import sys

import maya.cmds as cmds
# from playsound import playsound

# self.render_geo_whitelist = ["Render", "Muscles", "Fat"]


class ExportAnim:
    def __init__(
        self,
        geo_whitelist,
        usd_type="",
        output="/home/will/Downloads/test_usd_export/", # directory file is saved too
        root_type="",
        start_frame=None,
        end_frame=None,
        debug=False,
        export_rig=False,
        include_blendshapes=True,
        changelist_description=None,
    ):
        self.render_geo_whitelist = geo_whitelist
        self.output = output
        self.root_type = root_type
        self.debug = debug
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.usd_type = usd_type
        self.export_rig = export_rig
        self.frame_step = 1
        self.include_blendshapes = include_blendshapes
        self.changelist_description = changelist_description if changelist_description else "Animation Export"

        self.load_plugins()

        # set start frame to maya scene time range
        if not self.start_frame:
            # self.start_frame = cmds.playbackOptions(q=True, animationStartTime=True)  # full timeline
            self.start_frame = cmds.playbackOptions(q=True, minTime=True)  # playback field
        if not self.end_frame:
            # self.end_frame = cmds.playbackOptions(q=True, animationEndTime=True)  # full timeline
            self.end_frame = cmds.playbackOptions(q=True, maxTime=True)  # playback field
        print("\nSTART FRAME", self.start_frame)
        print('END FRAME', self.end_frame, "\n")

        self.export_anim(self.output)

    def get_joint_grps(self, character):
        def traverse(parent_path):
            attr_name = "joints_grp"
            found_items = []
            children = cmds.listRelatives(parent_path, children=True, fullPath=True)

            if not children:
                return found_items
        
            for child in children:
                attr_path = child+"."+attr_name
                if cmds.objExists(attr_path) == True and cmds.getAttr(attr_path) == True:
                    found_items.append(child)

                child_found_items = traverse(child)
                found_items.extend(child_found_items)

            return found_items

        joints_path = f"{character}|rig"
        character_paths = traverse(joints_path)
        return character_paths

    def get_characters(self):
        groups = cmds.ls("geo", long=True)
        print("found groups", groups, "\n")

        matching_groups = []
        characters = []

        for grp in groups:
            parent = cmds.listRelatives(grp, parent=True, fullPath=True)

            if parent:
                parent_name = parent[0]

                if parent_name.endswith("_rig"):
                    characters.append(parent_name[1:-4])
                    matching_groups.append(grp)

        if not characters and not matching_groups:
            print("ERROR: No parent group to geo found, make sure parent group of geo has _rig suffix \n")
        else:
            print("matching groups", matching_groups)
            print("characters:", characters, "\n")

        return (characters, matching_groups)

    def load_plugins(self):
        if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
            cmds.loadPlugin("mayaUsdPlugin")

    def export_anim(self, export_file_path):
        characters, matching_groups = self.get_characters()
        project_root = self.output

        project_root = os.path.normpath(project_root)

        for i, character in enumerate(characters):
            group_name = matching_groups[i]
            root_prim = cmds.listRelatives(group_name, parent=True)[0]
            children = cmds.listRelatives(group_name, children=True)

            filtered_children = [
                child for child in children if child in self.render_geo_whitelist
            ]
            if len(filtered_children) == 0:
                print(f"no groups match the whitelist: {self.render_geo_whitelist} \n")
                return

            print("filtered_children from whitelist", filtered_children)
            print("children groups:", children, "\n")

            # print("export file path:", export_file_path)
            shot_num = "1"
            shot_num = f"SH{shot_num.zfill(4)}"

            export_file_path = os.path.normpath(export_file_path)
            # export_file_path = export_file_path.format(project_root=project_root, shot_num=shot_num, character=character)
            export_file_path = f"{project_root}/{shot_num}/{character}/{character}"
            print("EXPORT FILE PATH", export_file_path)

            export_file_already_exists = os.path.exists(f"{project_root}/{shot_num}/{character}/")
            if export_file_already_exists:
                print("FILE ALREADY EXISTS, going to OVERWITE")

            export_dirname = os.path.dirname(export_file_path)

            if not os.path.exists(export_dirname):
                print(f"{export_dirname} does not exist. Making path")
                os.makedirs(export_dirname)

            print("\n")

            # make selection
            made_selection = False
            cmds.select(clear=True)
            if self.export_rig:
                for joint_grp in self.get_joint_grps(character+"_rig"):
                    cmds.select(joint_grp, add=True)
            self.set_usd_type(group_name, self.usd_type)

            self.set_usd_type(root_prim, self.root_type)
            for child in cmds.listRelatives(group_name, children=True):
                if not child in self.render_geo_whitelist:
                    continue

                child = f"{group_name}|{child}"
                cmds.select(child, add=True)
                self.set_usd_type(child, self.usd_type)
                made_selection = True
            if not made_selection:
                print(
                    f"ERROR: Could not file element of {self.render_geo_whitelist} in {group_name} \n"
)
                continue

            # export file
            export_args = {
                    "file":export_file_path,
                    "selection":True,
                    "defaultMeshScheme":"none",
                    "exportVisibility":False,
                    "exportUVs":False,
                    "exportMaterialCollections":False,
                    "shadingMode":"none",
                    "frameRange":(self.start_frame, self.end_frame),
                    "frameStride":self.frame_step,
                    "staticSingleSample":True,
            }

            if self.include_blendshapes:
                export_args.update({"exportBlendShapes":True})
            else:
                export_args.update({"exportBlendShapes":False})

            if self.export_rig:
                export_args.update({
                    "exportSkels":"auto",
                    "exportSkin":"auto",
                })

            print("EXPORTING USD...")
            print("USD export args:\n",export_args)

            cmds.mayaUSDExport(**export_args)

            # End the Maya session
            print("finished exporting file:", export_file_path)
        print("exported all characters(meshes)")
        cmds.confirmDialog(message="Export Finished", title="Export Finished")

    def set_usd_type(self, item, usd_type):
        attr_path = f"{item}.USD_typeName"
        if(cmds.objExists(attr_path)):
            cmds.setAttr(attr_path, usd_type, type="string")
        else: print(f"cant find {attr_path} not setting attr value: {usd_type}")
