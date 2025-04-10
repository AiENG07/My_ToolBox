import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
import configparser
import subprocess
import logging

window_title = "渗透测试工具箱 v0.1.0（内测版）"
about_text = """
        渗透测试工具箱 v0.1.0（内测版）
        
        一个基于Python和Tkinter的渗透测试工具箱
        
        特性:
        - 模块化设计
        - 配置驱动
        - 支持多种工具类型
        - 可扩展性
        
        作者: AiENG07
        """
# 设置日志
log_file = "log/app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ConfigManager:
    """管理配置文件的类"""
    def __init__(self, config_path):
        self.config_path = config_path
        self.current_dir = Path(sys.argv[0]).parent.resolve()
        self.config = configparser.ConfigParser()
        self.load_config()
        
    def _get_path(self, section, key):
        """获取路径并进行拼接"""
        if section in self.config and key in self.config[section]:
            return self.current_dir / self.config[section][key]
        return None

    def get_environment_path(self, env_name):
        """获取环境变量的路径"""
        return self._get_path('environments', env_name)

    def get_tool_path(self, tool_name):
        """获取工具的路径"""
        return self._get_path(tool_name, 'path')

    def load_config(self):
        """加载配置文件"""
        if not Path(self.config_path).exists():
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在!")
        self.config.read(self.config_path, encoding='utf-8')

    def save_config(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def get(self, section, key, default=None):
        """获取配置值"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def set(self, section, key, value):
        """设置配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)
        self.save_config()

    def get_environments(self):
        """获取所有环境变量配置"""
        return dict(self.config['environments']) if 'environments' in self.config else {}

    def get_all_tools(self):
        """获取所有工具的配置"""
        tools = []
        for section in self.config.sections():
            if section not in ['set', 'environments']:
                tools.append({
                    'name': section,
                    'category': self.config[section].get('category', ''),
                    'path': self.config[section].get('path', ''),
                    'type': self.config[section].get('type', ''),
                    'env': self.config[section].get('env', ''),
                    'args': self.config[section].get('args', ''),
                    'description': self.config[section].get('description', '')
                })
        return tools

    def add_tool(self, name, category, path, tool_type, env='', args='', description=''):
        """添加新工具到配置"""
        if name in self.config:
            logging.warning(f"工具 {name} 已存在，将覆盖")
        self.config[name] = {
            'category': category,
            'path': path,
            'type': tool_type,
            'env': env,
            'args': args,
            'description': description
        }
        self.save_config()

    def remove_tool(self, name):
        """从配置中移除工具"""
        if name in self.config:
            self.config.remove_section(name)
            self.save_config()

    def get_columns(self):
        """获取每行显示的工具数量"""
        return self.config.getint('set', 'columns', fallback=5)

    def set_columns(self, columns):
        """设置每行显示的工具数量"""
        self.set('set', 'columns', str(columns))

    def set_window_size(self, width, height):
        """设置窗口大小"""
        self.set('set', 'window_width', str(width))
        self.set('set', 'window_height', str(height))

class EnvironmentManager:
    """管理环境变量的类"""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.environments = self.config_manager.get_environments()
        self.current_dir = Path(sys.argv[0]).parent.resolve()

    def run_with_environment(self, tool_type, env_name='', path='', args=''):
        """使用指定环境运行工具"""
        env_path = self.config_manager.get_environment_path(env_name)

        path = self.current_dir / path
        cdpath = os.path.dirname(path)
        if not path.exists():
            messagebox.showerror("错误", f"工具路径 {path} 不存在")
            return

        try:
            if tool_type in ['py', 'python']:
                python_exe = Path(env_path, 'python.exe' if os.name == 'nt' else 'python').resolve()
                command = f'cd "{cdpath}" && "{python_exe}" "{path}" {args}'
                command = f'start cmd /k "{command}"'
            elif tool_type in ['java', 'jar']:
                java_exe = Path(env_path, 'java.exe' if os.name == 'nt' else 'java').resolve()
                command = f'cd "{cdpath}" && "{java_exe}" -jar "{path}" {args}'
            elif tool_type == 'jcmd':
                java_exe = Path(env_path, 'java.exe' if os.name == 'nt' else 'java').resolve()
                command = f'cd "{cdpath}" && "{java_exe}" -jar "{path}" {args}'
                command = f'start cmd /k "{command}"'
            elif tool_type == 'exe':
                command = f'cd "{cdpath}" && "{path}" {args}'
            elif tool_type == 'cmd':
                command = f'cd "{cdpath}" && "{path}" {args}'
                command = f'start cmd /k "{command}"'
            elif tool_type == 'bat':
                command = f'cd "{cdpath}" && cmd /c "{path}" {args}'
            else:
                messagebox.showerror("错误", f"不支持的工具类型: {tool_type}")
                return

            logging.info(f"使用命令: {command}")
            subprocess.Popen(command, shell=True)
        except Exception as e:
            messagebox.showerror("错误", f"执行工具时出错: {e}")
            logging.error(f"执行工具时出错: {e}")

class ToolManager:
    """管理工具的类"""
    def __init__(self, config_manager, environment_manager):
        self.config_manager = config_manager
        self.environment_manager = environment_manager

    def get_categories(self):
        """获取所有工具分类"""
        tools = self.config_manager.get_all_tools()
        categories = {}
        for tool in tools:
            category = tool['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(tool)
        return categories

    def run_tool(self, tool):
        """运行指定工具"""
        self.environment_manager.run_with_environment(
            tool['type'], tool['env'], tool['path'], tool['args']
        )

    def add_tool(self, name, category, path, tool_type, env='', args='', description=''):
        """添加新工具"""
        self.config_manager.add_tool(name, category, path, tool_type, env, args, description)

    def remove_tool(self, name):
        """移除工具"""
        self.config_manager.remove_tool(name)


class UIManager:
    """管理 UI 的类"""
    def __init__(self, root, tool_manager, config_manager):
        self.root = root
        self.tool_manager = tool_manager
        self.config_manager = config_manager
        self.buttons = {}
        self.categories_frame = None
        self.tools_frame = None
        self.current_category = None
        self.log_window = None
        self.search_var = tk.StringVar()
        self.sort_var = tk.StringVar(value="名称")

        self._setup_window()
        self._create_menu()
        self._create_main_ui()
        self.load_tools()

    def _setup_window(self):
        """设置窗口属性"""
        self.root.title(window_title)
        self._set_window_geometry(0.65, 0.65)
        self.root.resizable(True, True)
        self.root.bind("<Configure>", self.on_window_resize)
    
    def _set_window_geometry(self, width_ratio, height_ratio):
        """设置窗口大小和位置"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = int(screen_width * width_ratio)
        window_height = int(screen_height * height_ratio)
        
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2 - 100
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    def on_window_resize(self, event):
        """窗口大小变化时的处理"""
        if event.widget == self.root:
            columns = max(2, min(6, event.width // 200))
            self.config_manager.set_columns(columns)
            if self.current_category:
                self.show_category(self.current_category)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)

        # 文件菜单
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="打开配置文件", command=self.open_config_dialog)
        filemenu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=filemenu)

        # 编辑菜单
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="添加工具", command=self.add_tool_dialog)
        editmenu.add_command(label="删除工具", command=self.remove_tool_dialog)
        menubar.add_cascade(label="编辑", menu=editmenu)

        # 设置菜单
        settingmenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settingmenu)

        # 每行工具菜单
        columnsmenu = tk.Menu(menubar, tearoff=0)
        columns = self.config_manager.get_columns()
        for i in range(2, 7):
            columnsmenu.add_radiobutton(
                label=f"每行{i}个工具",
                command=lambda i=i: self.change_columns(i)
            )
        settingmenu.add_cascade(label="每行工具", menu=columnsmenu)

        # 窗口大小菜单
        size_menu = tk.Menu(menubar, tearoff=0)
        size_menu_map = {
            "1920x1080": (1920, 1080),
            "1600x900": (1600, 900),
            "1440x900": (1440, 900),
            "1366x768": (1366, 768),
            "1280x800": (1280, 800),
            "1024x768": (1024, 768),
            "800x600": (800, 600)}
        for label, (width, height) in size_menu_map.items():
            size_menu.add_command(
                label=label,
                command=lambda width=width, height=height: self.change_window_size(width, height))
        size_menu.add_command(
            label="自定义",
            command=self.custom_window_size)
        settingmenu.add_cascade(label="窗口大小", menu=size_menu)

        # 帮助菜单
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=helpmenu)

        # 日志菜单
        logmenu = tk.Menu(menubar, tearoff=0)
        logmenu.add_command(label="查看日志", command=self.show_log_window)
        menubar.add_cascade(label="日志", menu=logmenu)

        self.root.config(menu=menubar)

    def custom_window_size(self):
        """自定义窗口大小"""
        width = simpledialog.askinteger("窗口宽度", "请输入窗口宽度:", minvalue=800, maxvalue=3840)
        height = simpledialog.askinteger("窗口高度", "请输入窗口高度:", minvalue=600, maxvalue=2160)
        if width and height:
            self.change_window_size(width, height)

    def change_columns(self, columns):
        """改变每行工具数量"""
        self.config_manager.set_columns(columns)
        if self.current_category:
            self.show_category(self.current_category)

    def _create_main_ui(self):
        """创建主界面"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧分类列表
        left_frame = ttk.Frame(main_frame, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="工具分类", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        self.categories_frame = ttk.Frame(left_frame)
        self.categories_frame.pack(fill=tk.BOTH, expand=True)

        # 右侧工具列表
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 搜索框和排序功能
        search_sort_frame = ttk.Frame(right_frame)
        search_sort_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_sort_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(search_sort_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.search_var.trace_add("write", self.filter_tools)

        ttk.Label(search_sort_frame, text="排序:").pack(side=tk.LEFT, padx=(0, 5))
        sort_combo = ttk.Combobox(search_sort_frame, textvariable=self.sort_var, values=["名称", "类型", "描述"], state="readonly", width=10)
        sort_combo.pack(side=tk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_tools())

        self.category_title = ttk.Label(right_frame, text="", font=("Arial", 14, "bold"))
        self.category_title.pack(anchor=tk.W, pady=(0, 10))

        self.tools_count = ttk.Label(right_frame, text="")
        self.tools_count.pack(anchor=tk.W, pady=(0, 10))

        # 工具列表（带滚动条）
        tools_wrapper = ttk.Frame(right_frame)
        tools_wrapper.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tools_wrapper)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tools_canvas = tk.Canvas(tools_wrapper, yscrollcommand=scrollbar.set)
        self.tools_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tools_canvas.yview)

        self.tools_frame = ttk.Frame(self.tools_canvas)
        self.tools_canvas.create_window((0, 0), window=self.tools_frame, anchor="nw")
        self.tools_frame.bind("<Configure>", lambda e: self.tools_canvas.configure(scrollregion=self.tools_canvas.bbox("all")))

    def load_tools(self):
        """加载工具到 UI"""
        categories = self.tool_manager.get_categories()

        for widget in self.categories_frame.winfo_children():
            widget.destroy()

        # 添加“所有工具”分类
        all_tools_btn = ttk.Button(
            self.categories_frame,
            text="所有工具",
            width=20,
            command=lambda: self.show_category("所有工具")
        )
        all_tools_btn.pack(fill=tk.X, padx=5, pady=2)

        for category in categories:
            btn = ttk.Button(
                self.categories_frame,
                text=category,
                width=20,
                command=lambda c=category: self.show_category(c)
            )
            btn.pack(fill=tk.X, padx=5, pady=2)

        # 显示第一个分类的工具
        if categories:
            first_category = "所有工具"
            self.show_category(first_category)

    def show_category(self, category):
        """显示指定分类的工具"""
        self.current_category = category
        tools = []

        if category == "所有工具":
            tools = self.config_manager.get_all_tools()
        else:
            tools = self.tool_manager.get_categories().get(category, [])

        self.category_title.config(text=category)
        self.tools_count.config(text=f"工具数量: {len(tools)}")

        for widget in self.tools_frame.winfo_children():
            widget.destroy()

        if not tools:
            ttk.Label(self.tools_frame, text="该分类下没有工具").pack(pady=20)
            return

        self.filter_tools()

    def filter_tools(self, *args):
        """根据搜索和排序条件过滤工具"""
        if not self.current_category:
            return

        tools = []
        if self.current_category == "所有工具":
            tools = self.config_manager.get_all_tools()
        else:
            tools = self.tool_manager.get_categories().get(self.current_category, [])

        search_term = self.search_var.get().lower()
        sort_by = self.sort_var.get()

        # 过滤工具
        filtered_tools = [
            tool for tool in tools
            if (search_term in tool['name'].lower() or
                search_term in tool['type'].lower() or
                search_term in tool['description'].lower())
        ]

        # 排序工具
        if sort_by == "名称":
            filtered_tools.sort(key=lambda x: x['name'])
        elif sort_by == "类型":
            filtered_tools.sort(key=lambda x: x['type'])
        elif sort_by == "描述":
            filtered_tools.sort(key=lambda x: x['description'])

        # 显示过滤后的工具
        for widget in self.tools_frame.winfo_children():
            widget.destroy()

        if not filtered_tools:
            ttk.Label(self.tools_frame, text="没有匹配的工具").pack(pady=20)
            return

        columns = self.config_manager.get_columns()
        self._create_tool_buttons(filtered_tools, columns)

    def _create_tool_buttons(self, tools, columns):
        """创建工具按钮"""
        row, col = 0, 0
        for tool in tools:
            btn = ttk.Button(
                self.tools_frame,
                text=tool['name'],
                command=lambda t=tool: self.run_tool(t),
                width=20
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.tools_frame.grid_columnconfigure(col, weight=1)
            
            # 右键菜单
            btn.bind("<Button-3>", lambda event, t=tool: self.show_context_menu(event, t))

            col += 1
            if col >= columns:
                col = 0
                row += 1

    def show_context_menu(self, event, tool):
        """显示右键菜单"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="工具详情", command=lambda: self.show_tool_details(tool))
        context_menu.add_command(label="打开文件所在位置", command=lambda: self.open_file_location(tool))
        context_menu.post(event.x_root, event.y_root)

    def show_tool_details(self, tool):
        """显示工具详情"""
        details_window = tk.Toplevel(self.root)
        details_window.title(f"工具详情: {tool['name']}")
        details_window.geometry("400x500")
        details_window.resizable(False, False)
        details_window.transient(self.root)
        details_window.grab_set()

        # 设置窗口位置
        self._center_window(details_window, 400, 500)

        # 创建表单元素
        fields = [
            ("工具名称", tool['name']),
            ("分类", tool['category']),
            ("路径", tool['path']),
            ("类型", tool['type']),
            ("环境变量", tool['env']),
            ("参数", tool['args']),
            ("描述", tool['description'])
        ]

        for i, (label, value) in enumerate(fields):
            ttk.Label(details_window, text=f"{label}:", font=("Arial", 10, "bold")).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            entry = ttk.Entry(details_window, width=40) if i != 6 else tk.Text(details_window, width=30, height=10, wrap=tk.WORD)
            entry.grid(row=i, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
            entry.insert(0 if i != 6 else tk.END, value)
            entry.config(state='readonly' if i != 6 else 'disabled')

        ttk.Button(details_window, text="关闭", command=details_window.destroy).grid(row=len(fields), column=0, columnspan=2, pady=10)

    def _center_window(self, window, width, height):
        """将窗口居中显示"""
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        window_x = root_x + (root_width - width) // 2
        window_y = root_y + (root_height - height) // 2
        window.geometry(f"{width}x{height}+{window_x}+{window_y}")

    def open_file_location(self, tool):
        """打开文件所在位置"""
        file_path = Path(tool['path'])
        if not file_path.exists():
            messagebox.showerror("错误", f"文件路径 {file_path} 不存在")
            return

        try:
            if os.name == 'nt':
                os.startfile(file_path.parent)
            else:
                subprocess.Popen(['xdg-open', str(file_path.parent)])
        except Exception as e:
            messagebox.showerror("错误", f"打开文件位置时出错: {e}")
            logging.error(f"打开文件位置时出错: {e}")

    def run_tool(self, tool):
        """运行工具"""
        try:
            self.tool_manager.run_tool(tool)
        except Exception as e:
            messagebox.showerror("错误", f"运行工具时出错: {e}")
            logging.error(f"运行工具时出错: {e}")

    def open_config_dialog(self):
        """打开配置文件对话框"""
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("配置文件", "*.ini")]
        )
        if file_path:
            os.startfile(file_path)

    def add_tool_dialog(self):
        """添加工具对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加工具")
        dialog.geometry("400x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 设置窗口位置
        self._center_window(dialog, 400, 400)

        # 表单元素
        fields = [
            ("工具名称", tk.StringVar()),
            ("分类", tk.StringVar()),
            ("路径", tk.StringVar()),
            ("类型", tk.StringVar(value='exe')),
            ("环境变量", tk.StringVar()),
            ("参数", tk.StringVar()),
            ("描述", tk.StringVar())
        ]

        for i, (label, var) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            entry = ttk.Entry(dialog, textvariable=var)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky=tk.W+tk.E)
            if label == "路径":
                ttk.Button(dialog, text="浏览", command=lambda var=var: self.browse_file(var)).grid(row=i, column=2, padx=5, pady=5)
            if label == "分类":
                categories = list(self.tool_manager.get_categories().keys())
                entry = ttk.Combobox(dialog, textvariable=var, values=categories)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky=tk.W+tk.E)
            if label == "类型":
                entry = ttk.Combobox(dialog, textvariable=var, values=['exe', 'cmd', 'bat', 'jar', 'jcmd', 'python'])
                entry.grid(row=i, column=1, padx=10, pady=5, sticky=tk.W+tk.E)
            if label == "环境变量":
                env_options = list(self.config_manager.get_environments().keys())
                env_options.insert(0, "(无)")
                entry = ttk.Combobox(dialog, textvariable=var, values=env_options)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky=tk.W+tk.E)

        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=len(fields), column=0, columnspan=3, pady=10)
        ttk.Button(button_frame, text="保存", command=lambda: self.save_tool(dialog, fields)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        dialog.grid_columnconfigure(1, weight=1)

    def browse_file(self, var):
        """文件浏览对话框"""
        file_path = filedialog.askopenfilename()
        if file_path:
            var.set(file_path)

    def save_tool(self, dialog, fields):
        """保存工具配置"""
        data = {}
        for label, var in fields:
            value = var.get()
            if value == "(无)":
                data[label] = ""
            else:
                data[label] = value

        path = data["路径"]
        if not Path(path).exists():
            messagebox.showerror("错误", f"路径 {path} 不存在")
            return

        self.tool_manager.add_tool(
            data["工具名称"],
            data["分类"],
            data["路径"],
            data["类型"],
            data["环境变量"],
            data["参数"],
            data["描述"]
        )

        self.load_tools()
        dialog.destroy()
        messagebox.showinfo("成功", f"工具 {data['工具名称']} 已添加")

    def remove_tool_dialog(self):
        """删除工具对话框"""
        if not self.current_category:
            messagebox.showerror("错误", "请先选择一个分类")
            return

        tools = []
        if self.current_category == "所有工具":
            tools = self.config_manager.get_all_tools()
        else:
            tools = self.tool_manager.get_categories().get(self.current_category, [])

        if not tools:
            messagebox.showerror("错误", "当前分类下没有工具")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("删除工具")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 设置窗口位置
        self._center_window(dialog, 400, 300)

        ttk.Label(dialog, text="选择要删除的工具:").pack(pady=10)
        listbox = tk.Listbox(dialog, width=50, height=10)
        listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        for tool in tools:
            listbox.insert(tk.END, f"{tool['name']} - {tool['description']}")

        def delete_selected():
            selected_index = listbox.curselection()
            if not selected_index:
                messagebox.showerror("错误", "请先选择一个工具")
                return

            tool = tools[selected_index[0]]
            if messagebox.askyesno("确认", f"确定要删除工具 {tool['name']} 吗?"):
                self.tool_manager.remove_tool(tool['name'])
                self.load_tools()
                dialog.destroy()
                messagebox.showinfo("成功", f"工具 {tool['name']} 已删除")

        ttk.Button(dialog, text="删除", command=delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(dialog, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def change_window_size(self, width, height):
        """切换窗口大小"""
        self.config_manager.set_window_size(width, height)
        self._set_window_geometry(width / self.root.winfo_screenwidth(), height / self.root.winfo_screenheight())

    def show_about(self):
        """显示关于信息"""
        messagebox.showinfo("关于", about_text)

    def show_log_window(self):
        """显示日志窗口"""
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
            return

        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("运行日志")
        self._center_window(self.log_window, 800, 600)

        # 日志内容区域
        log_frame = ttk.Frame(self.log_window)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # 按钮区域
        button_frame = ttk.Frame(self.log_window)
        button_frame.pack(fill=tk.X, pady=5)

        current_dir = Path(sys.argv[0]).parent.resolve()
        log_file = current_dir / 'log/app.log'

        ttk.Button(button_frame, text="刷新", command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=self.log_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=lambda: self.log_text.config(state=tk.NORMAL, text="")).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="打开日志文件", command=lambda: os.startfile(log_file)).pack(side=tk.RIGHT, padx=5)

        # 自动刷新日志
        self.refresh_logs()
        self.log_window.after(1000, self.auto_refresh_logs)

    def refresh_logs(self):
        """刷新日志内容"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, log_content)
            self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("错误", f"刷新日志时出错: {e}")
            logging.error(f"刷新日志时出错: {e}")

    def auto_refresh_logs(self):
        """自动刷新日志"""
        if self.log_window and self.log_window.winfo_exists():
            self.refresh_logs()
            self.log_window.after(1000, self.auto_refresh_logs)

def main():
    current_dir = Path(sys.argv[0]).parent.resolve()
    config_path = current_dir / 'config.ini'

    log_file = current_dir / 'log/app.log'
    log_dir = current_dir / 'log'
    log_dir.mkdir(parents=True, exist_ok=True)

    config_manager = ConfigManager(config_path)
    environment_manager = EnvironmentManager(config_manager)
    tool_manager = ToolManager(config_manager, environment_manager)
    root = tk.Tk()
    ui_manager = UIManager(root, tool_manager, config_manager)
    root.mainloop()

if __name__ == "__main__":
    main()