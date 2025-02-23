import numpy as np
from moviepy import ImageSequenceClip, VideoFileClip
import wave
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import time
import sys
import os
from datetime import datetime

# 时间戳
now = datetime.now()
timestamp = now.timestamp()
print("当前时间戳：", timestamp)

# 创建一个隐藏的主窗口
root = tk.Tk()
root.withdraw()  # 隐藏主窗口

# 显示警告信息
messagebox.showwarning("警告！", "请不要在程序运行时删除本目录下的临时文件，否则会导致程序运行出错！")

# 循环直到用户确认文件选择正确
while True:
    file_path = filedialog.askopenfilename(
        title="请选择文件",
        filetypes=[("所有文件", "*.*")]
    )
    if file_path:
        result = messagebox.askyesno("确认", f"选中的文件路径是：\n{file_path}\n\n请确认是否正确")
        if result:
            print("文件选择已确认，继续后续操作...")
            break
        else:
            print("文件选择错误，重新选择文件...")
    else:
        print("没有选择文件，程序将在3秒后退出...")
        time.sleep(3)
        sys.exit()

print(f"选中的文件路径是：{file_path}")
whatpath = file_path

def get_input(prompt, error_message, additional_message=""):
    while True:
        user_input = simpledialog.askstring(prompt, f"请输入生成视频的{prompt}：{additional_message}")
        if user_input is None:
            print(f"未输入{prompt}，程序将在3秒后退出...")
            time.sleep(3)
            sys.exit()
        elif user_input.isdigit():
            return int(user_input)
        else:
            messagebox.showerror("错误", error_message)

whatfps = get_input("帧率", "请输入数字！")
whatel = get_input("边长", "请输入数字！", "（像素）（提示：会做放大处理，不用担心插值模糊）")
messagebox.showinfo("提示", "生成过程可能需要较长时间，请耐心等待... 可以在控制台中查看进度")

#还未使用的功能.....
def bytes_to_image(data, width, height):
    image = np.frombuffer(data, dtype=np.uint8)
    image = image[:width * height * 3]
    image = image.reshape((height, width, 3))
    return image

# 二进制文件转视频
def create_video_from_file(file_path, output_path, width=int(whatel), height=int(whatel), fps=int(whatfps)):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    frame_size = width * height * 3
    num_frames = len(data) // frame_size
    
    frames = []
    for i in range(num_frames):
        start = i * frame_size
        end = start + frame_size
        frame_data = data[start:end]
        frame = bytes_to_image(frame_data, width, height)
        frames.append(frame)
    
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(output_path, codec='libx264')
    clip.close()  # 确保释放资源

file_path = whatpath
video_output_path = 'video_temp_output.mp4'
create_video_from_file(file_path, video_output_path)
print(f"视频已生成，保存为{video_output_path}")

# 获取视频时长
def get_video_duration(output_path):
    clip = VideoFileClip(output_path)
    duration = clip.duration
    clip.close()  # 确保释放资源
    return duration

videolong = get_video_duration(video_output_path)

# 计算音频采样率
def calculate_audio_sample_rate(video_path, video_duration):
    clip = VideoFileClip(video_path)
    fps = clip.fps
    width, height = clip.size
    clip.close()  # 确保释放资源
    
    total_frames = int(video_duration * fps)
    frame_data_size = width * height * 3
    total_data_size = total_frames * frame_data_size
    sample_rate = total_data_size / video_duration / 2
    return sample_rate

sample_rate = calculate_audio_sample_rate(video_output_path, videolong)
# 将二进制数据转换为音频数据
def bytes_to_audio(data, sample_rate=int(sample_rate)):
    audio = np.frombuffer(data, dtype=np.int16)
    return audio

def create_audio_from_file(file_path, output_path, sample_rate=int(sample_rate)):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    audio_data = bytes_to_audio(data, sample_rate)
    
    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

file_path = whatpath
audio_output_path = 'audio_temp_output.wav'
create_audio_from_file(file_path, audio_output_path)
print(f"音频已生成，保存为{audio_output_path}")

# 合并视频和音频
def merge_video_audio(video_path, audio_path, output_path):
    FFmer = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        output_path
    ]
    try:
        subprocess.run(FFmer, check=True)
        print(f"合并完成，输出文件保存为{output_path}")
    except subprocess.CalledProcessError as e:
        print(f"合并失败：{e}")

video_path = video_output_path
audio_path = audio_output_path
nozoom_output_path = "nozoomtemp_output.mp4"
merge_video_audio(video_path, audio_path, nozoom_output_path)

# 放大视频
def resize_video(input_file, output_file, width, height):
    FFzoom = [
        "ffmpeg",
        "-i", input_file,
        "-vf", f"scale={width}:{height}:flags=neighbor",
        "-c:v", "libx264",
        "-crf", "18",
        "-c:a", "copy",
        output_file
    ]
    try:
        subprocess.run(FFzoom, check=True)
        print(f"视频已成功放大并保存到 {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"调用 FFmpeg 时出错: {e}")

input_file = nozoom_output_path
output_file = f"./output_{timestamp}.mp4"
resize_video(input_file, output_file, 768, 768)

# 安全删除临时文件
def safe_delete(file_path, retries=3, delay=2):
    for attempt in range(retries):
        try:
            os.remove(file_path)
            print(f"成功删除临时文件：{file_path}")
            return
        except PermissionError as e:
            print(f"删除文件时出错：{e}，尝试第 {attempt + 1} 次...")
            time.sleep(delay)
    print(f"无法删除文件：{file_path}，请手动删除。")


messagebox.showinfo("成功！", "视频已生成！")
time.sleep(1)

safe_delete(video_output_path)
safe_delete(audio_output_path)
safe_delete(nozoom_output_path)

print("已删除临时文件")

os._exit(0)
