import cv2
import numpy as np
import os
import requests
from bs4 import BeautifulSoup
import webbrowser
import json
import base64
import time
from collections import Counter
import re
import urllib.parse
from PIL import ImageFont, ImageDraw, Image
import bidi
import tkinter as tk
from tkinter import filedialog
import ctypes   

def get_image_path():
    root = tk.Tk()
    root.title("IMINT FPO - img Selection")
    root.geometry("400x100")
    
    root.configure(bg="black")
    
    main_frame = tk.Frame(root, padx=10, pady=10, bg="black")
    main_frame.pack(fill=tk.BOTH, expand=True,)
    
    tk.Label(main_frame, text="Image Path:", bg="black", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
    
    path_entry = tk.Entry(main_frame, width=40)
    path_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
    path_entry.insert(0, "image.png")
    
    def browse_file():
        filename = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if filename:
            path_entry.delete(0, tk.END)
            path_entry.insert(0, filename)
    
     
    browse_btn = tk.Button(main_frame, text="Browse...", command=browse_file, bg="black", fg="white")
    browse_btn.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
    
    result = {"path": None}
    
    def on_submit():
        result["path"] = path_entry.get()
        root.destroy()
    
     
    submit_btn = tk.Button(main_frame, text="START", command=on_submit, bg="red", fg="black")
    submit_btn.grid(row=5, column=0, columnspan=3, pady=10)
    
    main_frame.columnconfigure(1, weight=1)
    
    root.mainloop()
    return result["path"]

 
image_path = get_image_path()
if not image_path or not os.path.exists(image_path):
    print("Image not found or path is invalid!")
    exit()

image_original = cv2.imread(image_path)
if image_original is None:
    print("Failed to load image!")
    exit()

clone = image_original.copy()
padding = 100

def add_frame_to_image(img, padding):
    h, w = img.shape[:2]
    framed_img = np.full((h + 2*padding, w + 2*padding, img.shape[2]), (0, 0, 0), dtype=np.uint8)
    framed_img[padding:padding+h, padding:padding+w] = img
    return framed_img

image = add_frame_to_image(image_original, padding)

cv2.namedWindow("IMINT FPO", cv2.WINDOW_NORMAL)
 
cv2.setWindowProperty("IMINT FPO", cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_FREERATIO)
 
cv2.imshow("IMINT FPO", image)

ref_point = []
cropping = False
rectangles = []   
counter = 0       
saved_images = []   
saved_images_info = [] 
max_selections = 10
 
right_panel_width = 400   
right_panel_height = image.shape[0]
right_panel = np.zeros((right_panel_height, right_panel_width, 3), dtype=np.uint8)
scroll_offset = 0
scroll_step = 30
max_scroll = 0
scrolling_active = False
scroll_timeout = 0.5   
last_scroll_time = 0

def put_persian_text(img, text, position, font_size, color=(255, 255, 255)):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    
    try:
        font = ImageFont.truetype(font_size)
    except:
        font = ImageFont.load_default()
    
    try:
        text = bidi.algorithm.get_display(text)
    except:
        pass   
    
    draw.text(position, text, font=font, fill=color)
    
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img

def upload_image_to_freeimage(image_path):
    max_retries = 3
    retry_delay = 2   
    
    for attempt in range(max_retries):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {
                    "success": False,
                    "url": "",
                    "message": "Failed to read image"
                }
            
            height, width = img.shape[:2]
            max_size = 1024   
            
            if height > max_size or width > max_size:
                if height > width:
                    ratio = max_size / height
                else:
                    ratio = max_size / width
                
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = cv2.resize(img, (new_width, new_height))
                
                temp_path = f"temp_{os.path.basename(image_path)}"
                cv2.imwrite(temp_path, img)
                image_to_upload = temp_path
            else:
                image_to_upload = image_path
            
            with open(image_to_upload, "rb") as file:
                files = {
                    "source": (os.path.basename(image_to_upload), file, "image/png")
                }
                
                response = requests.post(
                    "https://freeimage.host/api/1/upload",
                    files=files,
                    data={
                        "key": "6d207e02198a847aa98d0a2a901485a5",
                        "action": "upload"
                    },
                    timeout=30   
                )
            
            if image_to_upload != image_path and os.path.exists(image_to_upload):
                os.remove(image_to_upload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("image", {}).get("url"):
                    image_url = result["image"]["url"]
                    return {
                        "success": True,
                        "url": image_url,
                        "message": "uploaded"
                    }
                else:
                    return {
                        "success": False,
                        "url": "",
                        "message": result.get("error", {}).get("message", "error")
                    }
            else:
                return {
                    "success": False,
                    "url": "",
                    "message": f"error HTTP: {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Upload attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return {
                "success": False,
                "url": "",
                "message": f"error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "url": "",
                "message": f"error: {str(e)}"
            }
    
    return {
        "success": False,
        "url": "",
        "message": "Max upload retries reached"
    }
 
def upload_image(image_path): 
    print("Trying with freeimage.host...")
    result = upload_image_to_freeimage(image_path)
    return result
 
def analyze_image_with_majidapi(image_path):
    max_retries = 3
    retry_delay = 3   
    
    for attempt in range(max_retries):
        try:
            upload_result = upload_image(image_path)
            if not upload_result["success"]:
                return {
                    "success": False,
                    "message": upload_result["message"],
                    "result": "",
                    "persian_result": ""
                }
            
            image_url = upload_result["url"]
         
            api_url = f"https://api.majidapi.ir/ai/photo-analysis?photo={image_url}&token=8f9fjv91fxmyebs%3Agr7nO0cVFb0qrWyHCLPE"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(api_url, headers=headers, timeout=60)   
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("status") == 200 and "result" in result:
                        full_result = result["result"]
                        
                        if not full_result or not full_result.strip():
                            return {
                                "success": False,
                                "message": "Empty analysis result",
                                "result": "",
                                "persian_result": ""
                            }
                        
                        english_analysis = ""
                        start_marker_en = ["Analysis in English 🇺🇸", "Image Analysis (English)", "Analysis in English", "English"]
                        found_marker = None
                        start_index = -1
                        
                        for marker in start_marker_en:
                            if marker in full_result:
                                found_marker = marker
                                start_index = full_result.find(marker)
                                break   
                        
                        if found_marker is not None:
                            start_index += len(found_marker)
                            english_analysis = full_result[start_index:].strip()
                            
                            if english_analysis.startswith(":"):
                                english_analysis = english_analysis[1:].strip()
                        else:
                            english_analysis = full_result
                         
                        persian_analysis = ""
                        start_marker_fa = "تحلیل به فارسی 🇮🇷"
                        if start_marker_fa in full_result:
                            start_index = full_result.find(start_marker_fa) + len(start_marker_fa)
                            persian_analysis = full_result[start_index:].strip()
                            
                            if persian_analysis.startswith(":"):
                                persian_analysis = persian_analysis[1:].strip()
                        
                        return {
                            "success": True,
                            "message": "ok image",
                            "result": english_analysis,
                            "persian_result": persian_analysis
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"API error: {result.get('message', 'Unknown error')}",
                            "result": "",
                            "persian_result": ""
                        }
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {str(e)}")
                    print(f"Response content: {response.text[:500]}...")   
                    return {
                        "success": False,
                        "message": "error API response",
                        "result": "",
                        "persian_result": ""
                    }
            else:
                print(f"HTTP error: {response.status_code}")
                print(f"Response content: {response.text[:500]}...")   
                return {
                    "success": False,
                    "message": f"error HTTP: {response.status_code}",
                    "result": "",
                    "persian_result": ""
                }
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Analysis attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return {
                "success": False,
                "message": f"Request error: {str(e)}",
                "result": "",
                "persian_result": ""
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"error: {str(e)}",
                "result": "",
                "persian_result": ""
            }
    
    return {
        "success": False,
        "message": "Max analysis retries reached",
        "result": "",
        "persian_result": ""
    }
 
def search_and_analyze_image(image_path):
    upload_result = upload_image(image_path)
    analysis_result = analyze_image_with_majidapi(image_path)
    image_info = {
        'url': upload_result.get('url', ''),
        'upload_success': upload_result.get('success', False),
        'upload_message': upload_result.get('message', ''),
        'result': analysis_result.get('result', ''),
        'persian_result': analysis_result.get('persian_result', ''),
        'analysis_success': analysis_result.get('success', False),
        'analysis_message': analysis_result.get('message', '')
    }
    
    return image_info

def update_right_panel():
    global right_panel, saved_images, saved_images_info, scroll_offset, max_scroll
    
     
    extended_height = right_panel_height * 3   
    extended_panel = np.zeros((extended_height, right_panel_width, 3), dtype=np.uint8)
    
    remaining = max_selections - len(saved_images)
    extended_panel = put_persian_text(extended_panel, f"Selected img : {remaining}", (10, 20), 10, (255, 255, 255))
    
    if not saved_images:
         
        scroll_offset = 0
        max_scroll = 0
        right_panel = np.zeros((right_panel_height, right_panel_width, 3), dtype=np.uint8)
        update_combined_image()
        return
    
    y_offset = 40
    total_content_height = 40   
    
    for i, (img, info) in enumerate(zip(saved_images, saved_images_info)):
        img_height = max(50, min(100, 150))   
        img_width = int(img.shape[1] * (img_height / img.shape[0]))
        
        if img_width > right_panel_width - 20:
            img_width = right_panel_width - 20
            img_height = int(img.shape[0] * (img_width / img.shape[1]))
        
        resized_img = cv2.resize(img, (img_width, img_height))
        
         
        if y_offset + img_height <= extended_height:
            extended_panel[y_offset:y_offset+img_height, 10:10+img_width] = resized_img
            extended_panel = put_persian_text(extended_panel, f"#{i+1}", (10, y_offset + 1), 14, (255, 0, 0))
        
        info_x = img_width + 20
        info_y = y_offset + -10
        
        if info.get('url', ''):
            english_result_text = info.get('result', '')
            if english_result_text:
                info_y += 5
                
                max_lines = 10   
                lines = english_result_text.split('\n')
                line_count = 0
                
                for line in lines:
                    if line_count >= max_lines:
                        break
                        
                    if len(line) > 50:
                        words = line.split(' ')
                        current_line = ""
                        for word in words:
                            test_line = current_line + word + " "
                            if len(test_line) > 50:
                                if current_line:   
                                    extended_panel = put_persian_text(extended_panel, current_line, (info_x, info_y), 12, (200, 200, 200))
                                    info_y += 15
                                    line_count += 1
                                    if line_count >= max_lines:
                                        break
                                current_line = word + " "
                            else:
                                current_line = test_line
                        
                        if current_line and line_count < max_lines:
                            extended_panel = put_persian_text(extended_panel, current_line, (info_x, info_y), 12, (200, 200, 200))
                            info_y += 15
                            line_count += 1
                    else:
                        extended_panel = put_persian_text(extended_panel, line, (info_x, info_y), 12, (200, 200, 200))
                        info_y += 15
                        line_count += 1
                
                if line_count >= max_lines and len(lines) > max_lines:
                    extended_panel = put_persian_text(extended_panel, "...", (info_x, info_y), 12, (200, 200, 200))
                    info_y += 15
        else:
            extended_panel = put_persian_text(extended_panel, "Upload failed", (info_x, info_y), 14, (0, 0, 255))
            info_y += 20
            
            message = info.get('upload_message', '')
            if message:
                words = message.split(' ')
                line = ""
                for word in words:
                    test_line = line + word + " "
                    if len(test_line) > 50:
                        extended_panel = put_persian_text(extended_panel, line, (info_x, info_y), 12, (200, 200, 200))
                        info_y += 15
                        line = word + " "
                    else:
                        line = test_line
                extended_panel = put_persian_text(extended_panel, line, (info_x, info_y), 12, (200, 200, 200))
                info_y += 20
        
         
        item_height = img_height + 50
        total_content_height += item_height
        y_offset += item_height
    
     
    max_scroll = max(0, total_content_height - right_panel_height)
    
     
    scroll_offset = max(0, min(scroll_offset, max_scroll))
    
     
    right_panel = extended_panel[scroll_offset:scroll_offset + right_panel_height, :]
    
     
    if max_scroll > 0:
        scrollbar_width = 10
        scrollbar_x = right_panel_width - scrollbar_width
        scrollbar_height = right_panel_height
        scrollbar_ratio = scrollbar_height / (scrollbar_height + max_scroll)
        scrollbar_handle_height = int(scrollbar_height * scrollbar_ratio)
        scrollbar_handle_y = int(scroll_offset * scrollbar_ratio)
        
         
        cv2.rectangle(right_panel, (scrollbar_x, 0), (scrollbar_x + scrollbar_width, scrollbar_height), (50, 50, 50), -1)
        
         
        cv2.rectangle(right_panel, (scrollbar_x, scrollbar_handle_y), 
                     (scrollbar_x + scrollbar_width, scrollbar_handle_y + scrollbar_handle_height), (150, 150, 150), -1)
    
    update_combined_image() 
 
def update_combined_image():
    combined = np.hstack((image, right_panel))
    line_color = (200, 200, 200)
    line_thickness = 2
    cv2.line(combined, (image.shape[1], 0), (image.shape[1], combined.shape[0]), line_color, line_thickness)
    cv2.imshow("IMINT FPO", combined)

def shape_selection(event, x, y, flags, param):
    global ref_point, cropping, image, image_original, clone, rectangles, counter, saved_images, saved_images_info
    global scroll_offset, scroll_step, max_scroll, scrolling_active, last_scroll_time
    
     
    current_time = time.time()
    if scrolling_active and (current_time - last_scroll_time) < scroll_timeout:
        return
    
     
    if scrolling_active and (current_time - last_scroll_time) >= scroll_timeout:
        scrolling_active = False
    
     
    if event == cv2.EVENT_MOUSEWHEEL:
        scrolling_active = True
        last_scroll_time = current_time
        
        if flags > 0:   
            scroll_offset = max(0, scroll_offset - scroll_step)
        else:   
            scroll_offset = min(max_scroll, scroll_offset + scroll_step)
        update_right_panel()
        return
    
     
    if scrolling_active:
        return
    
    if x < padding or x >= image.shape[1] - padding or y < padding or y >= image.shape[0] - padding:
        return
    
    x -= padding
    y -= padding
    
    if len(saved_images) >= max_selections:
        return
    
    if event == cv2.EVENT_LBUTTONDOWN:
        ref_point = [(x, y)]
        cropping = True
    
    elif event == cv2.EVENT_MOUSEMOVE:
        if cropping:
            temp_img = image_original.copy()
            for rect in rectangles:
                cv2.rectangle(temp_img, rect[0], rect[1], (0, 0, 255), 2)
            cv2.rectangle(temp_img, ref_point[0], (x, y), (0, 0, 255), 2)
            image = add_frame_to_image(temp_img, padding)
            update_combined_image()
    
    elif event == cv2.EVENT_LBUTTONUP:
        cropping = False
        ref_point.append((x, y))
        
        rectangles.append((ref_point[0], ref_point[1]))
        
        roi = image_original[ref_point[0][1]:ref_point[1][1], ref_point[0][0]:ref_point[1][0]]
        
        counter += 1
        
        roi_filename = f"images/img_{counter}.png"
        
        cv2.imwrite(roi_filename, roi)
        print(f"Selected region saved as {roi_filename}")
        
        saved_images.append(roi)
        
        image_info = search_and_analyze_image(roi_filename)
        saved_images_info.append(image_info)
        
        print(f"Image #{counter} info:")
        print(f"URL: {image_info.get('url', 'N/A')}")
        print(f"Upload Message: {image_info.get('upload_message', 'N/A')}")
        print(f"Analysis Message: {image_info.get('analysis_message', 'N/A')}")
        
        english_analysis = image_info.get('result', '')
        if english_analysis:
            print("English Analysis:")
            print(f"  {english_analysis}")
        
        print("-" * 50)
        
        update_right_panel()
        
        temp_img = image_original.copy()
        for rect in rectangles:
            cv2.rectangle(temp_img, rect[0], rect[1], (0, 0, 255), 2)
        image = add_frame_to_image(temp_img, padding)
        update_combined_image()
        
        if len(saved_images) >= max_selections:
            print(f"Maximum selections reached: ({max_selections})")
 
cv2.setMouseCallback("IMINT FPO", shape_selection)
 
update_right_panel()
update_combined_image()

while True:
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord("r"):
        image_original = clone.copy()
        image = add_frame_to_image(image_original, padding)
        rectangles = []
        counter = 0
        saved_images = []
        saved_images_info = []
        scroll_offset = 0
        max_scroll = 0
        scrolling_active = False
        update_right_panel()
        update_combined_image()
        print("All selections cleared")
    
    elif key == ord("q"):
        break
    
     
    elif key == 82:   
        scrolling_active = True
        last_scroll_time = time.time()
        scroll_offset = max(0, scroll_offset - scroll_step)
        update_right_panel()
    
    elif key == 84:   
        scrolling_active = True
        last_scroll_time = time.time()
        scroll_offset = min(max_scroll, scroll_offset + scroll_step)
        update_right_panel()

cv2.destroyAllWindows()
print(f"Total {counter} regions saved in 'images' folder")
