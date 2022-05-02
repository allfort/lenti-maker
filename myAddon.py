import os
import bpy
import mathutils
import queue
import math
from math import radians
from bpy_extras.io_utils import ExportHelper

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

    FOCUS_OBJ_NAME = 'Focus'            # 焦点オブジェクトの名前
    PIVOT_OBJ_NAME = 'LentiPivot'       # レンダリングカメラの回転中心オブジェクト名
    RENDER_CAM_NAME = 'LentiCamera'     # レンダリングカメラのオブジェクト名

    @classmethod
    def get_focus_location(cls, context):
        camera = get_scene_camera()
        camera_dir = (camera.rotation_euler.to_quaternion() * mathutils.Vector((0, 0, -1))).normalized()
        return camera.location + context.scene.focusDist * camera_dir

    # 焦点オブジェクトを作成する
    @classmethod
    def create_focus_object(cls, context):
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        pivot_obj = context.active_object
        pivot_obj.name = cls.FOCUS_OBJ_NAME
        # レントゲン設定
        pivot_obj.show_x_ray = True
        return pivot_obj

    # 焦点オブジェクトを取得する
    @classmethod
    def get_focus_object(cls):
        for obj in bpy.data.objects:
            if obj.name == cls.FOCUS_OBJ_NAME:
                return obj

    # レンダリングカメラのピボットを作成する
    @classmethod
    def create_pivot_object(cls, context):
        bpy.ops.object.empty_add(type='SPHERE')
        pivot_obj = context.active_object
        pivot_obj.name = cls.PIVOT_OBJ_NAME
        pivot_obj.empty_draw_size = 0.01
        return pivot_obj

    # レンダリングカメラを作成する
    @classmethod
    def create_render_camera(cls, number):
        render_camera = duplicate(get_scene_camera())
        render_camera.name = cls.get_render_camera_name(number)
        # サイズを小さめにしておく
        bpy.types.Camera(render_camera.data).draw_size = 0.6
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

        # 焦点オブジェクトの位置を更新する
        if cls.get_focus_object() is not None:
            # 一旦カメラと焦点オブジェクトの親子関係を切る
            clear_parent(cls.get_focus_object())
            # 焦点オブジェクトの位置更新
            cls.get_focus_object().location = cls.get_focus_location(context)
            cls.get_focus_object().rotation_euler = get_scene_camera().rotation_euler
            # 親子関係を再設定
            set_parent_keep_transform(cls.get_focus_object(), get_scene_camera())

        for i in range(cam_num):
            cam = cls.get_render_camera(i)

            # まだ作成してなければ
            if cam is None:
                # レンダリングカメラの原点を焦点位置に設定する
                priv_cursor_location = bpy.context.scene.cursor_location.copy()  # 3Dカーソルの位置を記憶しておく
                bpy.context.scene.cursor_location = cls.get_focus_location(context)

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

                # pivotをシーンカメラの子に設定する
                set_parent_keep_transform(pivot, get_scene_camera())

            # 既に作成済みのカメラがあれば
            else:
                pivot = cam.parent

                # 一旦カメラとpivotの親子関係を切る
                clear_parent(cam)

                # カメラ・回転中心オブジェクトを焦点位置に応じて再設定する
                pivot.location = cls.get_focus_location(context)
                pivot.rotation_euler = get_scene_camera().rotation_euler

                # カメラ姿勢を一旦シーンカメラに戻す
                cam.location = get_scene_camera().location
                cam.rotation_euler = get_scene_camera().rotation_euler

                # pivotをレンダリングカメラの親に設定する
                set_parent_keep_transform(cam, pivot)

                # カメラ位置を設定する
                angle_diff = i * cam_angle_dist - (cam_num - 1) * cam_angle_dist / 2.0
                cam.parent.rotation_euler.rotate_axis('Y', radians(angle_diff))

                # pivotをシーンカメラの子に設定する
                set_parent_keep_transform(pivot, get_scene_camera())

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
        # シーンカメラが存在するなら実行可能
        return get_scene_camera() is not None

    def execute(self, context):
        # 焦点オブジェクトを作成
        focus = self.create_focus_object(context)
        focus.location = self.get_focus_location(context)

        # 焦点オブジェクトをシーンカメラの子供に
        set_parent_keep_transform(focus, get_scene_camera())

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


# ビューでオブジェクトを非表示にする
def hide_object_in_view(object):
    # 全オブジェクトの選択解除
    bpy.ops.object.select_all(action='DESELECT')

    # オブジェクト選択
    object.select = True
    bpy.context.scene.objects.active = object

    # 非表示にする
    bpy.context.object.hide = True


# 出力フォルダのベースディレクトリを取得する
def get_output_base_directory():
    return os.path.join(bpy.context.scene.outputDirectory, 'LentiMakerOutput')


# 出力先が設定されているか
def is_select_output_directory():
    return len(bpy.context.scene.outputDirectory) is not 0


# 画像を別ウィンドウで開く
def show_image(image_path):
    os.system('start %s' % image_path)


# 画像をスクリーン上に印刷サイズで表示する
def open_image_print_size(image_file, context):
    # レンチキュラー画像のパスを取得
    image_file = LENTI_OT_GenerateResultImage.get_result_image_path()

    # 画面解像度・画像解像度取得
    screen_resolution_x = context.scene.screenResolutionX
    image_resolution_x = bpy.data.images.load(image_file).size[0]

    # 画面サイズ・印刷画像サイズ算出
    screen_size_inch = context.scene.screenSizeInch
    screen_ratio_x, screen_ratio_y = map(int, context.scene.screenRatio.split(':'))
    screen_width_cm = 2.54 * screen_size_inch / math.sqrt(1 + pow(screen_ratio_y / screen_ratio_x, 2))
    print_width_cm = context.scene.printWidthCm

    # 画像表示時の倍率算出
    view_scale = (screen_resolution_x / image_resolution_x) * (print_width_cm / screen_width_cm)

    # 画像を開く
    open_image_new_window(image_file, view_scale)


# 画像を別ウィンドウで開く
def open_image_new_window(image_file, scale_factor):
    bpy.ops.screen.area_dupli('INVOKE_DEFAULT')
    area = bpy.context.window_manager.windows[-1].screen.areas[0]
    area.type = 'IMAGE_EDITOR'
    area.spaces[0].image = bpy.data.images.load(image_file)

    override = {'area': area}
    bpy.ops.image.view_zoom_ratio(override, ratio=scale_factor)


# レンダリングする
class LENTI_OT_Rendering(bpy.types.Operator):
    bl_idname = "lenti.rendering"
    bl_label = "撮影"
    bl_description = "配置したカメラでレンダリングします。"
    bl_options = {'REGISTER', 'UNDO'}

    timer = None            # 定期実行のためのタイマー
    is_cancel = None        # レンダリングがキャンセルされたかどうか
    is_rendering = None     # レンダリング中かどうか
    render_queue = None     # レンダリング待ちカメラのキュー
    priv_scene_cam = None   # レンダリング開始前のアクティブカメラを保持しておく

    # 出力先ディレクトリを取得する
    @classmethod
    def get_output_directory(cls):
        return os.path.join(get_output_base_directory(), 'RenderResult')

    # レンダリングした画像のパスのリストを取得する
    @classmethod
    def get_rendered_image_path_list(cls):
        return [os.path.join(cls.get_output_directory(), f) for f in os.listdir(cls.get_output_directory())]

    # 指定したカメラでレンダリングする
    @classmethod
    def render(cls, camera):
        # 出力先ディレクトリがなければ作成する
        if not os.path.isdir(cls.get_output_directory()):
            os.makedirs(cls.get_output_directory())

        bpy.context.scene.camera = camera
        print('render %s' % camera.name)
        file = os.path.join(cls.get_output_directory(), camera.name)
        bpy.context.scene.render.filepath = file

        # レンダリング
        bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)

    # 配置したカメラでレンダリングする
    def start_rendering(self):
        print("start rendering...")
        self.is_cancel = False
        self.is_rendering = False

        # 元のシーンカメラを記憶しておく
        self.priv_scene_cam = get_scene_camera()

        # レンダリングカメラを登録
        self.render_queue = queue.Queue()
        for cam in bpy.data.objects:
            if cam.type == 'CAMERA' and cam.name in [LENTI_OT_BuildStudio.get_render_camera_name(i) for i in
                                                     range(bpy.context.scene.camNum)]:
                self.render_queue.put(cam)

        # レンダリング状況通知を受け取るためのハンドラー登録
        bpy.app.handlers.render_pre.append(self.pre)
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.canceled)

        # レンダリング状況を監視するための定期処理登録
        self.timer = bpy.context.window_manager.event_timer_add(1.0, window=bpy.context.window)
        bpy.context.window_manager.modal_handler_add(self)

    @classmethod
    def poll(cls, context):
        # 出力先が選択されていれば
        if not is_select_output_directory():
            return False

        # レンダリング用カメラがあれば
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA' and obj.name in [LENTI_OT_BuildStudio.get_render_camera_name(i) for i in
                                                     range(context.scene.camNum)]:
                return True
        return False

    def pre(self, dummy, thrd=None):
        print('pre')

    def post(self, dummy, thrd=None):
        print('post')
        self.is_rendering = False

    def canceled(self, dummy, thrd=None):
        print('canceled')
        self.is_cancel = True

    def modal(self, context, event):
        if event.type == 'TIMER':
            print('modal')

            if (self.render_queue.empty() and self.is_rendering is False) or self.is_cancel:
                print('finish')
                # ハンドラー解除
                bpy.app.handlers.render_pre.remove(self.pre)
                bpy.app.handlers.render_post.remove(self.post)
                bpy.app.handlers.render_cancel.remove(self.canceled)
                bpy.context.window_manager.event_timer_remove(self.timer)

                # シーンカメラを元に戻す
                bpy.context.scene.camera = self.priv_scene_cam

                return {'FINISHED'}
            else:
                if self.is_rendering is False:
                    self.is_rendering = True
                    self.render(self.render_queue.get())
                else:
                    # レンダリングが開始されてない事があるためレンダリングを定期的にコールする
                    bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)

        return {'PASS_THROUGH'}

    def execute(self, context):
        # レンダリング開始
        self.start_rendering()

        return {'RUNNING_MODAL'}


# 設定反映
class LENTI_OT_ApplySetting(bpy.types.Operator):
    bl_idname = "lenti.apply_setting"
    bl_label = "設定反映"
    bl_description = "印刷・レンチキュラープロパティの設定を反映します。"
    bl_options = {'REGISTER', 'UNDO'}

    # レンダリング画像の解像度を算出する
    @classmethod
    def trans_mm_to_pixel(cls, x_mm, y_mm, dpi):
        inch_mm = 25.4
        return x_mm * dpi / inch_mm, y_mm * dpi / inch_mm

    def execute(self, context):
        # レンダリング解像度設定
        render_width, render_height = self.trans_mm_to_pixel(context.scene.printWidthCm * 10, context.scene.printHeightCm * 10, context.scene.DPI)

        scene = bpy.data.scenes["Scene"]
        scene.render.resolution_x = render_width
        scene.render.resolution_y = render_height
        scene.render.resolution_percentage = 100

        return {'FINISHED'}


# 結果のレンチキュラー用画像を生成する
class LENTI_OT_GenerateResultImage(bpy.types.Operator):
    bl_idname = "lenti.generate_result_image"
    bl_label = "レンチキュラー画像生成"
    bl_description = "レンチキュラー画像を生成する"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def get_result_image_path(cls):
        file_name = 'result'
        suffix = '.png'
        return os.path.join(get_output_base_directory(), file_name + suffix)

    # レンチキュラー画像生成
    def generate(self, context):
        # 出力画像読み込み
        rendered_image_path_list = LENTI_OT_Rendering.get_rendered_image_path_list()
        image_list = [bpy.data.images.load(path, check_existing=False) for path in rendered_image_path_list]
        pixels_list = [list(img.pixels[:]) for img in image_list]

        # 出力画像作成
        new_image = bpy.data.images.new("result", width=image_list[0].size[0], height=image_list[0].size[1])

        width = new_image.size[0]
        height = new_image.size[1]
        pixels = [None] * width * height

        # ピクセル設定
        image_count = len(image_list)
        px_per_lenz = int(context.scene.DPI / context.scene.LPI)
        for x in range(width):
            img_select = math.floor(x * image_count / px_per_lenz) % (image_count - 1)
            for y in range(height):
                r = pixels_list[img_select][y * (width * 4) + x * 4 + 0]
                g = pixels_list[img_select][y * (width * 4) + x * 4 + 1]
                b = pixels_list[img_select][y * (width * 4) + x * 4 + 2]
                a = pixels_list[img_select][y * (width * 4) + x * 4 + 3]

                pixels[(y * width) + x] = [r, g, b, a]

        # flatten list
        pixels = [chan for px in pixels for chan in px]

        # assign pixels
        new_image.pixels = pixels

        new_image.filepath_raw = self.get_result_image_path()
        new_image.file_format = image_list[0].file_format
        new_image.save()

    @classmethod
    def poll(cls, context):
        return is_select_output_directory()

    def execute(self, context):
        self.generate(context)

        # 生成完了時に画像を開く
        open_image_print_size(self.get_result_image_path(), context)

        return {'FINISHED'}


# 出力先を選択する
class LENTI_OT_SelectOutputDirectory(bpy.types.Operator, ExportHelper):
    bl_idname = "lenti.select_output_directory"
    bl_label = "出力先選択"

    filename_ext = ""

    def execute(self, context):
        context.scene.outputDirectory = self.properties.filepath
        return {'FINISHED'}


# ツールシェルフにタブを追加
class LENTI_PT_Menu(bpy.types.Panel):
    bl_label = "LentiMaker"     # タブに表示される文字列
    bl_space_type = "VIEW_3D"   # 表示するエリア
    bl_region_type = "TOOLS"    # 表示するリージョン
    bl_category = "LentiMaker"  # タブを開いた時のヘッダーに表示される文字列
    bl_context = "objectmode"   # パネルを表示するコンテキスト

    # 焦点距離更新時に呼び出される
    def onFocusDistUpdate(self, context):
        # カメラ位置を更新する
        LENTI_OT_BuildStudio.arrange_camera(context)

    # 焦点距離設定プロパティを表示するかどうか
    @classmethod
    def isDispFocusDistProperty(cls):
        return True

    # レンダリングカメラ数更新時に呼び出される
    def onCamNumUpdate(self, context):
        LENTI_OT_BuildStudio.arrange_camera(context)

    # レンダリングカメラ数設定プロパティを表示するかどうか
    @classmethod
    def isDispCamNumProperty(cls):
        return True

    # レンダリングカメラの配置間隔更新時に呼び出される
    def onCameraAngleDiffUpdate(self, context):
        LENTI_OT_BuildStudio.arrange_camera(context)

    # レンダリングカメラの配置間隔設定プロパティを表示するかどうか
    @classmethod
    def isDispCamAngleDiffProperty(cls):
        return True

    # 印刷DPIプロパティ（1インチあたりに何個ドット並んでいるかという解像度の単位）
    bpy.types.Scene.DPI = bpy.props.IntProperty(default=300, name='DPI', min=100)

    # レンチキュラーLPIプロパティ（1インチあたりに何個レンズ（かまぼこ）があるかという単位）
    bpy.types.Scene.LPI = bpy.props.IntProperty(default=60, name='LPI', min=10)

    # 印刷サイズプロパティ(cm)
    bpy.types.Scene.printWidthCm = bpy.props.FloatProperty(default=9.1, name='PrintWidthCm', min=1.0)
    bpy.types.Scene.printHeightCm = bpy.props.FloatProperty(default=5.5, name='PrintHeightCm', min=1.0)

    # 焦点距離設定プロパティ
    bpy.types.Scene.focusDist = bpy.props.FloatProperty(default=3.0, name='FocusDist', min=1.0, update=onFocusDistUpdate)

    # レンダリングカメラ数設定プロパティ
    bpy.types.Scene.camNum = bpy.props.IntProperty(default=2, name='camNum', min=2, update=onCamNumUpdate)

    # レンダリングカメラ配置間隔設定プロパティ
    bpy.types.Scene.camAngleDiff = bpy.props.FloatProperty(default=30.0, name='camAngleDiff', min=1.0, update=onCameraAngleDiffUpdate)

    # 出力先プロパティ
    bpy.types.Scene.outputDirectory = bpy.props.StringProperty()

    # PCの画面解像度プロパティ
    bpy.types.Scene.screenResolutionX = bpy.props.IntProperty(default=1920, name='ScreenResolutionX', min=100)
    bpy.types.Scene.screenResolutionY = bpy.props.IntProperty(default=1080, name='ScreenResolutionY', min=100)

    # PCの画面サイズプロパティ
    bpy.types.Scene.screenSizeInch = bpy.props.FloatProperty(default=24.0, name='ScreenSizeInch', min=12.1)
    bpy.types.Scene.screenRatio = bpy.props.StringProperty(default='16:9', name='ScreenRatio')

    # メニューの描画処理
    def draw(self, context):

        self.layout.label(text="設定")

        # 印刷設定プロパティ
        self.layout.prop(context.scene, "DPI")

        # レンチキュラーレンズ設定プロパティ
        self.layout.prop(context.scene, "LPI")

        # レンチキュラーのレンズ1かまぼこ当たりの画像ピクセル数を表示する
        # この値が視差画像の制限枚数となる
        px_per_lenz = context.scene.DPI / context.scene.LPI
        self.layout.label(text="1レンズあたり %f px" % px_per_lenz)

        # 1レンズあたりのピクセル数が整数でなければ注意表示をする
        if not px_per_lenz.is_integer():
            self.layout.label(text="1レンズあたりのピクセル数が整数になるよう設定してください。", icon='ERROR')

        # 印刷サイズ
        self.layout.prop(context.scene, "printWidthCm")
        self.layout.prop(context.scene, "printHeightCm")

        # 設定反映ボタン
        self.layout.operator(LENTI_OT_ApplySetting.bl_idname)

        self.layout.separator()     # ------------------------------------------

        # 焦点設定ボタン
        self.layout.operator(LENTI_OT_BuildStudio.bl_idname)

        # 焦点距離プロパティ
        if self.isDispFocusDistProperty():
            self.layout.prop(context.scene, "focusDist")

        # カメラ数設定
        if self.isDispCamNumProperty():
            self.layout.prop(context.scene, "camNum")

        # レンダリングカメラ数が不適切であれば注意表示
        max_cam_num = context.scene.DPI / context.scene.LPI
        if context.scene.camNum > max_cam_num:
            self.layout.label(text="カメラ数は %d 以下に設定してください。" % max_cam_num, icon='ERROR')
        if not (max_cam_num / context.scene.camNum).is_integer():
            self.layout.label(text="カメラ数は最大値 %d を割り切れる数に設定してください。" % max_cam_num, icon='ERROR')

        # カメラ配置間隔設定
        if self.isDispCamAngleDiffProperty():
            self.layout.prop(context.scene, "camAngleDiff")

        self.layout.separator()     # ------------------------------------------

        # 出力先選択
        col = self.layout.column()
        row = col.row(align=True)
        row.prop(context.scene, "outputDirectory", text='出力先')
        row.operator(LENTI_OT_SelectOutputDirectory.bl_idname, icon="FILE_FOLDER", text="")

        # 出力先が選択されてなければ注意表示
        if not is_select_output_directory():
            self.layout.label(text="出力先を選択してください。", icon='ERROR')

        # 撮影ボタン
        self.layout.operator(LENTI_OT_Rendering.bl_idname)

        # 出力画像一覧
        image_path_list = LENTI_OT_Rendering.get_rendered_image_path_list()

        if len(image_path_list) > 0:
            self.layout.label(text="出力画像一覧")

        for i in range(len(image_path_list)):
            self.layout.label(text="[" + str(i) + "] " + image_path_list[i])

        self.layout.separator()     # ------------------------------------------

        # レンチキュラー画像生成ボタン
        self.layout.operator(LENTI_OT_GenerateResultImage.bl_idname)

        self.layout.separator()  # ------------------------------------------

        # 解像度プロパティ
        self.layout.prop(context.scene, "screenResolutionX")
        self.layout.prop(context.scene, "screenResolutionY")

        # 画面サイズプロパティ
        self.layout.prop(context.scene, "screenSizeInch")
        self.layout.prop(context.scene, "screenRatio")


def register():
    bpy.utils.register_module(__name__)


if __name__ == "__main__":
    register()
