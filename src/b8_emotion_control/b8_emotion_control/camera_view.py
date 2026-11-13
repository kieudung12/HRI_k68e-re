"""Cửa sổ webcam bằng Tkinter; chỉ hiển thị và nhận thao tác giao diện."""

import time
import tkinter as tk

import cv2
from PIL import Image, ImageTk


# Tên, hành động và gợi ý này cũng là bảng chú giải cho người làm bài.
EXPRESSIONS = {
    'happy': ('Vui vẻ', 'Cong trái', 'Cười rõ, nâng hai khóe miệng.', '#41d6aa'),
    'sad': ('Buồn', 'Cong phải', 'Hạ khóe miệng, thả lỏng và nhìn thẳng.', '#78a9ff'),
    'neutral': ('Bình thường', 'Dừng tại chỗ', 'Thả lỏng mặt, khép nhẹ môi.', '#a8b8ce'),
    'angry': ('Tức giận', 'Lùi nhẹ', 'Hạ lông mày, hơi cau mày và mím môi.', '#ff9b87'),
    'surprise': ('Ngạc nhiên', 'Xoay một vòng', 'Mở to mắt và mở miệng hình chữ O.', '#bb9bff'),
    'fear': ('Sợ hãi', 'Tiến nhẹ', 'Nâng lông mày, mở mắt và kéo căng môi.', '#f4c66a'),
}
BG, PANEL, BORDER = '#0b1120', '#131e30', '#26354c'
TEXT, MUTED, ACCENT = '#edf3fc', '#9aacc4', '#41d6aa'


class CameraView:
    def __init__(self, on_close, on_pause, on_threshold, confidence=35.0,
                 on_calibrate=None, on_clear=None):
        self.window = tk.Tk()
        self.window.title('HRI · Face Motion | Bài 08')
        self.window.configure(bg=BG)
        self.window.geometry('1240x850')
        self.window.minsize(1080, 760)
        self.window.protocol('WM_DELETE_WINDOW', on_close)
        self.window.bind('<Escape>', on_close)
        self.window.bind('<KeyPress-q>', on_close)
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)
        self.mirror = tk.BooleanVar(value=True)
        self.last_frame = time.monotonic()
        self.photo = None

        header = tk.Frame(self.window, bg=BG)
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(20, 16))
        self._label(header, 'HRI LAB  /  BÀI THỰC HÀNH 08', 10, MUTED).pack(anchor='w')
        self._label(header, 'Biểu cảm dẫn lối chuyển động', 23, TEXT, bold=True).pack(anchor='w', pady=(3, 0))
        self.live = self._label(header, '●  WEBCAM TRỰC TIẾP', 10, ACCENT)
        self.live.place(relx=1.0, rely=0.5, anchor='e')

        body = tk.Frame(self.window, bg=BG)
        body.grid(row=1, column=0, sticky='nsew', padx=24)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, minsize=340)

        camera = self._panel(body)
        camera.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        camera.grid_columnconfigure(0, weight=1)
        camera.grid_rowconfigure(1, weight=1)
        title = tk.Frame(camera, bg=PANEL)
        title.grid(row=0, column=0, sticky='ew', padx=16, pady=12)
        self._label(title, 'Góc nhìn của bạn', 12, TEXT, bold=True).pack(side='left')
        self.metrics = self._label(title, 'Đang chờ camera', 9, MUTED)
        self.metrics.pack(side='right')
        self.video = tk.Canvas(camera, bg='#070c15', width=800, height=450,
                               highlightthickness=0)
        self.video.grid(row=1, column=0, sticky='nsew')
        self.image_item = self.video.create_image(0, 0, anchor='center')
        bottom = tk.Frame(camera, bg=PANEL)
        bottom.grid(row=2, column=0, sticky='ew', padx=16, pady=12)
        self.hint = self._label(bottom, 'Đưa mặt vào giữa khung hình, nhìn thẳng và giữ biểu cảm.', 10, MUTED)
        self.hint.configure(wraplength=670, justify='left')
        self.hint.pack(anchor='w')
        controls = tk.Frame(bottom, bg=PANEL)
        controls.pack(fill='x', pady=(7, 0))
        tk.Checkbutton(controls, text='Lật gương', variable=self.mirror, bg=PANEL,
                       fg=MUTED, selectcolor=BG, activebackground=PANEL,
                       activeforeground=TEXT, font=('DejaVu Sans', 9),
                       highlightthickness=0).pack(side='left')
        self.calibrate = tk.Button(controls, text='Lấy mẫu Bình thường', command=on_calibrate,
                                   bg=BORDER, fg=TEXT, activebackground='#344761',
                                   activeforeground=TEXT, relief='flat', padx=10, pady=5,
                                   font=('DejaVu Sans', 9), cursor='hand2')
        self.calibrate.pack(side='right')
        self.clear = tk.Button(controls, text='Xóa mẫu', command=on_clear, bg=PANEL,
                               fg=MUTED, activebackground=PANEL, activeforeground=TEXT,
                               relief='flat', font=('DejaVu Sans', 9), cursor='hand2')
        self.clear.pack(side='right', padx=8)
        self.calibration_note = self._label(bottom, 'Chưa lấy mẫu mặt bình thường', 9, MUTED)
        self.calibration_note.pack(anchor='w', pady=(5, 0))

        sidebar = self._panel(body)
        sidebar.configure(width=340)
        sidebar.grid_propagate(False)
        sidebar.grid(row=0, column=1, sticky='nsew')
        sidebar.grid_columnconfigure(0, weight=1)
        self._label(sidebar, 'KẾT QUẢ NHẬN DIỆN', 9, MUTED).grid(row=0, column=0, sticky='w', padx=18, pady=(16, 5))
        self.emotion = self._label(sidebar, 'Đang quan sát', 23, TEXT, bold=True)
        self.emotion.grid(row=1, column=0, sticky='w', padx=18)
        self.confirmation = self._label(sidebar, 'Chưa có khuôn mặt', 10, MUTED)
        self.confirmation.configure(wraplength=285, justify='left')
        self.confirmation.grid(row=2, column=0, sticky='w', padx=18, pady=(3, 12))
        self.robot = self._label(sidebar, '●  Chưa kết nối robot', 10, MUTED)
        self.robot.configure(wraplength=285, justify='left')
        self.robot.grid(row=3, column=0, sticky='ew', padx=18, pady=(0, 12))
        tk.Frame(sidebar, bg=BORDER, height=1).grid(row=4, column=0, sticky='ew', padx=18)
        self.score_title = self._label(sidebar, 'Điểm của từng biểu cảm', 10, TEXT, bold=True)
        self.score_title.grid(
            row=5, column=0, sticky='w', padx=18, pady=(12, 8))
        self.bars = {}
        bar_box = tk.Frame(sidebar, bg=PANEL)
        bar_box.grid(row=6, column=0, sticky='ew', padx=18)
        for label in [*EXPRESSIONS, 'disgust']:
            name, _, _, color = EXPRESSIONS.get(label, ('Khác / ghê tởm', '', '', MUTED))
            row = tk.Frame(bar_box, bg=PANEL)
            row.pack(fill='x', pady=3)
            self._label(row, name, 9, MUTED).pack(side='left')
            value = self._label(row, '0%', 9, MUTED)
            value.pack(side='right')
            bar = tk.Canvas(bar_box, width=260, height=4, bg=BORDER, highlightthickness=0)
            bar.pack(fill='x', pady=(0, 2))
            fill = bar.create_rectangle(0, 0, 0, 4, fill=color, outline='')
            self.bars[label] = (bar, fill, value)
        settings = tk.Frame(sidebar, bg=PANEL)
        settings.grid(row=7, column=0, sticky='ew', padx=18, pady=(10, 5))
        self.threshold_text = self._label(settings, '', 9, MUTED)
        self.threshold_text.configure(wraplength=285, justify='left')
        self.threshold_text.pack(anchor='w')

        def change_threshold(value):
            self.threshold_text.configure(text=f'Ngưỡng chấp nhận: {float(value):.0f}%  ·  thấp hơn = nhạy hơn')
            on_threshold(float(value))

        self.threshold = tk.Scale(settings, from_=25, to=65, orient='horizontal',
                                  showvalue=False, command=change_threshold,
                                  bg=PANEL, fg=TEXT, troughcolor=BORDER,
                                  activebackground=ACCENT, highlightthickness=0,
                                  bd=0, sliderlength=18)
        self.threshold.set(confidence)
        self.threshold.pack(fill='x')
        self.pause = tk.Button(sidebar, text='Tạm dừng điều khiển', command=on_pause,
                               bg=ACCENT, fg=BG, activebackground='#6ce5c0',
                               font=('DejaVu Sans', 10, 'bold'), relief='flat',
                               cursor='hand2', pady=8)
        self.pause.grid(row=8, column=0, sticky='ew', padx=18, pady=(0, 14))

        guide = tk.Frame(self.window, bg=BG)
        guide.grid(row=2, column=0, sticky='ew', padx=24, pady=(16, 0))
        self.guide = self._label(guide, 'THỬ MỘT BIỂU CẢM  ·  Bấm thẻ để xem gợi ý', 10, MUTED)
        self.guide.pack(anchor='w', pady=(0, 8))
        cards = tk.Frame(guide, bg=BG)
        cards.pack(fill='x')
        self.cards = {}
        for column, (label, (name, action, tip, color)) in enumerate(EXPRESSIONS.items()):
            cards.grid_columnconfigure(column, weight=1, uniform='expression')
            button = tk.Button(cards, text=f'{name}\n{action}',
                               command=lambda text=f'{name}: {tip}': self.guide.configure(text=text, fg=TEXT),
                               bg=PANEL, fg=TEXT, activebackground=BORDER,
                               activeforeground=TEXT, relief='flat', bd=0,
                               font=('DejaVu Sans', 10), justify='left', anchor='w',
                               padx=13, pady=11, cursor='hand2',
                               highlightthickness=1, highlightbackground=BORDER)
            button.grid(row=0, column=column, sticky='ew', padx=(0 if column == 0 else 7, 0))
            self.cards[label] = button

        footer = tk.Frame(self.window, bg=BG)
        footer.grid(row=3, column=0, sticky='ew', padx=24, pady=(14, 18))
        self._label(footer, 'SPACE  Tạm dừng / tiếp tục     ·     Q / ESC  Đóng camera', 9, MUTED).pack(side='left')
        tk.Button(footer, text='Dừng & đóng', command=on_close, bg=BG, fg='#ff9b87',
                  activebackground=PANEL, activeforeground='#ffb5a6', bd=0,
                  font=('DejaVu Sans', 10), cursor='hand2').pack(side='right')
        # Bắt Space trước binding mặc định của Button, tránh tạm dừng hai lần.
        def pause_key(event):
            on_pause()
            return 'break'

        def bind_pause(widget):
            widget.bind('<space>', pause_key)
            for child in widget.winfo_children():
                bind_pause(child)

        bind_pause(self.window)
        self.window.update_idletasks()

    @staticmethod
    def _label(parent, text, size, color, bold=False):
        return tk.Label(parent, text=text, fg=color, bg=parent['bg'],
                        font=('DejaVu Sans', size, 'bold' if bold else 'normal'), bd=0, anchor='w')

    @staticmethod
    def _panel(parent):
        return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

    def render(self, frame, *, region, scores, accepted, hint, state, connected,
               fps, latency, paused, progress, required, calibrating=False,
               calibrated=False, calibration_note='', raw_prediction=None,
               needs_calibration=False):
        image = frame.copy()
        height, width = image.shape[:2]
        if region:
            x, y, w, h = (int(region[k]) for k in ('x', 'y', 'w', 'h'))
            cv2.rectangle(image, (x, y), (x+w, y+h), (170, 214, 65), 2)
        if self.mirror.get():
            image = cv2.flip(image, 1)
        canvas_w, canvas_h = max(1, self.video.winfo_width()), max(1, self.video.winfo_height())
        ratio = min(canvas_w / width, canvas_h / height)
        image = cv2.resize(image, (max(1, int(width*ratio)), max(1, int(height*ratio))))
        self.photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
        self.video.itemconfigure(self.image_item, image=self.photo)
        self.video.coords(self.image_item, canvas_w/2, canvas_h/2)
        self.metrics.configure(text=f'{width} × {height}  ·  {fps:.0f} FPS  ·  AI {latency:.0f} ms')
        self.hint.configure(wraplength=max(300, canvas_w-32))
        self.hint.configure(text=hint)
        name, action, _, color = EXPRESSIONS.get(accepted, ('Đang quan sát', 'Chờ biểu cảm rõ hơn', '', TEXT))
        self.emotion.configure(text=name, fg=color)
        if needs_calibration and not calibrating:
            self.emotion.configure(text='Chờ lấy mẫu', fg='#f4c66a')
        confirmation = ('Đã xác nhận biểu cảm' if accepted != 'NONE'
                                         else f'Đang ổn định: {min(progress, required)}/{required}' if progress
                                         else 'Chưa có lệnh chuyển động')
        if calibrated:
            confirmation = 'Đã hiệu chỉnh mặt bình thường'
            if raw_prediction:
                raw_label, raw_score = raw_prediction
                raw_name = EXPRESSIONS.get(raw_label, ('Khác', '', '', ''))[0]
                confirmation += f'\nModel gốc: {raw_name} {raw_score:.0f}%'
        if calibrating:
            confirmation = 'Giữ mặt thả lỏng khoảng 3 giây'
        elif needs_calibration:
            confirmation = 'Thả lỏng mặt, bấm nút Lấy mẫu Bình thường để bắt đầu.'
        self.confirmation.configure(text=confirmation)
        self.calibration_note.configure(text=calibration_note,
                                        fg='#f4c66a' if calibrating else ACCENT if calibrated else MUTED)
        self.calibrate.configure(text='Lấy lại từ đầu' if calibrating else
                                 'Lấy lại mẫu Bình thường' if calibrated else 'Lấy mẫu Bình thường')
        self.calibrate.configure(bg=ACCENT if needs_calibration and not calibrating else BORDER,
                                 fg=BG if needs_calibration and not calibrating else TEXT)
        self.clear.configure(state='normal' if calibrated or calibrating else 'disabled')
        self.score_title.configure(text='Điểm điều khiển sau hiệu chỉnh' if calibrated else 'Điểm của từng biểu cảm')
        if calibrating:
            robot_text, robot_color = '●  Đang lấy mẫu · robot dừng', '#f4c66a'
        elif needs_calibration:
            robot_text, robot_color = '●  Chờ hiệu chỉnh · robot dừng', '#f4c66a'
        elif paused:
            robot_text, robot_color = '●  Đã tạm dừng điều khiển', '#f4c66a'
        elif not connected:
            robot_text, robot_color = '●  Chưa kết nối node điều khiển', MUTED
        elif state.startswith('RUN'):
            active = state.split('|')[-1].strip()
            robot_action = EXPRESSIONS.get(active, ('', action, '', ''))[1]
            robot_text, robot_color = '●  Đang chạy · ' + robot_action, ACCENT
        else:
            robot_text, robot_color = '●  Đang dừng', MUTED
            if 'completed' in state or 'return to neutral' in state:
                robot_text = '●  Đã dừng · về Bình thường trước lượt mới'
            if 'odom' in state:
                robot_text = '●  Chưa nhận dữ liệu vị trí từ robot'
        self.robot.configure(text=robot_text, fg=robot_color)
        self.pause.configure(text='Lấy mẫu Bình thường' if needs_calibration and not calibrating else
                             'Tiếp tục điều khiển' if paused else 'Tạm dừng điều khiển')
        self.pause.configure(state='disabled' if calibrating else 'normal')
        self.live.configure(text='●  ĐANG HIỆU CHỈNH' if calibrating else
                            '●  TẠM DỪNG ĐIỀU KHIỂN' if paused else '●  WEBCAM TRỰC TIẾP',
                            fg='#f4c66a' if paused or calibrating else ACCENT)
        for label, (bar, fill, value) in self.bars.items():
            score = float(scores.get(label, 0))
            bar.coords(fill, 0, 0, max(1, bar.winfo_width())*score/100, 4)
            value.configure(text=f'{score:.0f}%', fg=TEXT if label == accepted else MUTED)
        for label, card in self.cards.items():
            card.configure(highlightbackground=EXPRESSIONS[label][3] if label == accepted else BORDER,
                           bg='#20384a' if label == accepted else PANEL)
        self.window.update()

    def close(self):
        self.window.destroy()
