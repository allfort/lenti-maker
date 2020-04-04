import bpy
import mathutils
from math import radians

# アドオンに関する情報を保持する、bl_info変数
bl_info = {
    "name": "サンプル2-2: オブジェクトを生成するアドオン",
    "author": "Allfort",
    "version": (2, 0),
    "blender": (2, 78, 0),
    "location": "3Dビュー > 追加 > メッシュ",
    "description": "オブジェクトを生成するサンプルアドオン",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

# 撮影用のスタジオを構築する
class LENTI_OT_BuildStudio(bpy.types.Operator):
    bl_idname = "lenti.build_studio"
    bl_label = "撮影スタジオ構築"
    bl_description = "レンチキュラー撮影するためのスタジオを構築します。"
    bl_options = {'REGISTER', 'UNDO'}

    FOCUS_OBJ_NAME = 'LentiFocus'       # 焦点オブジェクトのオブジェクト名
    PIVOT_OBJ_NAME = 'LentiPivot'       # レンダリングカメラの回転中心オブジェクト名
    RENDER_CAM_NAME = 'LentiCamera'     # レンダリングカメラのオブジェクト名

    # レンダリングカメラの焦点オブジェクトを作成する
    @classmethod
    def create_focus_object(cls, context):
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        pivot_obj = context.active_object
        pivot_obj.name = cls.FOCUS_OBJ_NAME
        return pivot_obj

    # 焦点オブジェクトを取得する
    @classmethod
    def get_focus_object(cls):
        for obj in bpy.data.objects:
            if obj.name == cls.FOCUS_OBJ_NAME:
                return obj
        return None

    # 焦点距離を設定する
    @classmethod
    def set_focus_dist(cls, focusDist):
        focus = cls.get_focus_object()
        if focus is None:
            return

        # 焦点オブジェクトの位置を更新する
        camera = get_scene_camera()
        camera_dir = (camera.rotation_euler.to_quaternion() * mathutils.Vector((0, 0, -1))).normalized()
        focus.location = camera.location + focusDist * camera_dir

    # レンダリングカメラの焦点オブジェクトを作成する
    @classmethod
    def create_pivot_object(cls, context):
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        pivot_obj = context.active_object
        pivot_obj.name = cls.PIVOT_OBJ_NAME
        return pivot_obj

    # レンダリングカメラを作成する
    @classmethod
    def create_render_camera(cls, number):
        render_camera = duplicate(get_scene_camera())
        render_camera.name = cls.get_render_camera_name(number)
        return render_camera

    # レンダリングカメラのオブジェクト名を取得する
    @classmethod
    def get_render_camera_name(cls, number):
        return cls.RENDER_CAM_NAME + "_" + str(number)

    # レンダリングカメラを取得する
    @classmethod
    def get_render_camera(cls, number):
        for obj in bpy.data.objects:
            if obj.name == cls.get_render_camera_name(number):
                return obj
        return None

    # レンダリングカメラを設定に従って並べる
    @classmethod
    def arrange_camera(cls, context):
        cam_num = context.scene.camNum
        cam_angle_dist = context.scene.camAngleDiff

        for i in range(cam_num):
            cam = cls.get_render_camera(i)

            # まだ作成してなければ
            if cam is None:
                # レンダリングカメラの原点を焦点位置に設定する
                priv_cursor_location = bpy.context.scene.cursor_location.copy()  # 3Dカーソルの位置を記憶しておく
                bpy.context.scene.cursor_location = cls.get_focus_object().location

                # 焦点位置にカメラの回転中心オブジェクトを作成する（オブジェクトの原点変更と同じだが、カメラの原点位置は変えられないため）
                pivot = cls.create_pivot_object(context)
                pivot.rotation_euler = get_scene_camera().rotation_euler

                # レンダリングカメラを作成する
                render_camera = cls.create_render_camera(i)

                # pivotをレンダリングカメラの親に設定する
                set_parent_keep_transform(render_camera, pivot)

                # カメラの配置位置を設定する
                angle_diff = i * cam_angle_dist - (cam_num - 1) * cam_angle_dist / 2.0
                pivot.rotation_euler.rotate_axis('Y', radians(angle_diff))

                # 3Dカーソルの位置を元に戻す
                bpy.context.scene.cursor_location = priv_cursor_location

            # 既に作成済みのカメラがあれば
            else:
                pivot = cam.parent

                # 一旦カメラとpivotの親子関係を切る
                clear_parent(cam)

                # カメラ・回転中心オブジェクトを焦点位置に応じて再設定する
                pivot.location = cls.get_focus_object().location
                pivot.rotation_euler = get_scene_camera().rotation_euler

                # カメラ姿勢を一旦シーンカメラに戻す
                cam.location = get_scene_camera().location
                cam.rotation_euler = get_scene_camera().rotation_euler

                # pivotをレンダリングカメラの親に設定する
                set_parent_keep_transform(cam, pivot)

                # カメラ位置を設定する
                angle_diff = i * cam_angle_dist - (cam_num - 1) * cam_angle_dist / 2.0
                cam.parent.rotation_euler.rotate_axis('Y', radians(angle_diff))

        # 不要なカメラを破棄する
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA' and cls.RENDER_CAM_NAME in obj.name and obj.name not in [cls.get_render_camera_name(i) for i in range(cam_num)]:
                # 全オブジェクトの選択解除
                bpy.ops.object.select_all(action='DESELECT')
                if obj.parent is not None:
                    obj.parent.select = True
                obj.select = True
                bpy.ops.object.delete()

    @classmethod
    def poll(cls, context):
        # シーンカメラが存在する & まだ焦点オブジェクトがないなら実行可能
        is_exist_scene_camera = get_scene_camera() is not None
        is_exist_focus_object = cls.get_focus_object() is not None
        return is_exist_scene_camera and not is_exist_focus_object

    def execute(self, context):
        # カメラの焦点オブジェクトを作成
        focus = self.create_focus_object(context)

        # カメラの前方に焦点オブジェクトを移動
        camera = get_scene_camera()
        camera_dir = (camera.rotation_euler.to_quaternion() * mathutils.Vector((0, 0, -1))).normalized()
        focus.location = camera.location + context.scene.focusDist * camera_dir

        # カメラを並べる
        self.arrange_camera(context)

        return {'FINISHED'}


# シーンで設定されたカメラを取得する
def get_scene_camera():
    return bpy.context.scene.camera


# 指定したオブジェクトを複製する
def duplicate(object):
    new_obj = object.copy()
    new_obj.data = object.data.copy()
    bpy.context.scene.objects.link(new_obj)
    return new_obj


# トランスフォームを維持して親子設定する
def set_parent_keep_transform(child, parent):
    # 全オブジェクトの選択解除
    bpy.ops.object.select_all(action='DESELECT')

    # 親子設定するオブジェクト選択
    child.select = True
    parent.select = True
    bpy.context.scene.objects.active = parent

    # 親子設定
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)


# 親子を解除する
def clear_parent(child):
    # 全オブジェクトの選択解除
    bpy.ops.object.select_all(action='DESELECT')

    # 親子オブジェクト選択
    child.select = True
    child.parent.select = True
    bpy.context.scene.objects.active = child.parent

    # 親子設定解除
    bpy.ops.object.parent_clear(type='CLEAR')


# ツールシェルフにタブを追加
class LENTI_PT_Menu(bpy.types.Panel):
    bl_label = "LentiMaker"     # タブに表示される文字列
    bl_space_type = "VIEW_3D"   # 表示するエリア
    bl_region_type = "TOOLS"    # 表示するリージョン
    bl_category = "LentiMaker"  # タブを開いた時のヘッダーに表示される文字列
    bl_context = "objectmode"   # パネルを表示するコンテキスト

    # 焦点距離更新時に呼び出される
    def onFocusDistUpdate(self, context):
        focusDist = context.scene.focusDist
        # 焦点オブジェクト位置を更新する
        LENTI_OT_BuildStudio.set_focus_dist(focusDist)
        # カメラ位置を更新する
        LENTI_OT_BuildStudio.arrange_camera(context)

    # 焦点距離設定プロパティを表示するかどうか
    @classmethod
    def isDispFocusDistProperty(cls):
        return LENTI_OT_BuildStudio.get_focus_object() is not None

    # レンダリングカメラ数更新時に呼び出される
    def onCamNumUpdate(self, context):
        LENTI_OT_BuildStudio.arrange_camera(context)

    # レンダリングカメラ数設定プロパティを表示するかどうか
    @classmethod
    def isDispCamNumProperty(cls):
        return LENTI_OT_BuildStudio.get_focus_object() is not None

    # レンダリングカメラの配置間隔更新時に呼び出される
    def onCameraAngleDiffUpdate(self, context):
        LENTI_OT_BuildStudio.arrange_camera(context)

    # レンダリングカメラの配置間隔設定プロパティを表示するかどうか
    @classmethod
    def isDispCamAngleDiffProperty(cls):
        return LENTI_OT_BuildStudio.get_focus_object() is not None

    # 焦点距離設定プロパティ
    bpy.types.Scene.focusDist = bpy.props.FloatProperty(default=3.0, name='FocusDist', min=1.0, update=onFocusDistUpdate)

    # レンダリングカメラ数設定プロパティ
    bpy.types.Scene.camNum = bpy.props.IntProperty(default=2, name='camNum', min=2, update=onCamNumUpdate)

    # レンダリングカメラ配置間隔設定プロパティ
    bpy.types.Scene.camAngleDiff = bpy.props.FloatProperty(default=30.0, name='camAngleDiff', min=15.0, update=onCameraAngleDiffUpdate)

    # メニューの描画処理
    def draw(self, context):
        # 焦点設定ボタン
        self.layout.operator(LENTI_OT_BuildStudio.bl_idname)

        # 焦点距離プロパティ
        if self.isDispFocusDistProperty():
            self.layout.prop(context.scene, "focusDist")

        # カメラ数設定
        if self.isDispCamNumProperty():
            self.layout.prop(context.scene, "camNum")

        # カメラ配置間隔設定
        if self.isDispCamAngleDiffProperty():
            self.layout.prop(context.scene, "camAngleDiff")


def register():
    bpy.utils.register_module(__name__)


if __name__ == "__main__":
    register()
