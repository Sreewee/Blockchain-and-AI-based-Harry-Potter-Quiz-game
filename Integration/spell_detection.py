import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import math
from flask import Flask, Response, render_template
import threading
import time

app = Flask(__name__)

# Global variables for the application
frame_lock = threading.Lock()
output_frame = None
gesture_detected = None

def detect_gestures():
    global output_frame, gesture_detected
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7)
    mp_drawing = mp.solutions.drawing_utils

    # For gesture detection
    finger_tip_ids = [4, 8, 12]  # thumb(4), Index (8), Middle (12)
    position_history = deque(maxlen=30)
    swipe_threshold = 110 
    curve_threshold = 0.3
    min_curve_points = 12
    cooldown_frames = 60 
    frame_count = 0
    swipe_detected = False
    curve_detected = False
    cooldown_counter = 0
    pinch_threshold = 80  # Max distance between fingers to consider a pinch

    # New state variables for combined gestures
    last_swipe = None
    last_curve = None
    combo_detected = False

    cap = cv2.VideoCapture(0)

    def detect_curve(positions):
        if len(positions) < min_curve_points:
            return None
        
        direction_changes = []
        cross_products = []
        
        for i in range(1, len(positions)-1):
            v1 = (positions[i][0] - positions[i-1][0], 
                positions[i][1] - positions[i-1][1])
            v2 = (positions[i+1][0] - positions[i][0], 
                positions[i+1][1] - positions[i][1])
            
            if v1[0] == 0 and v1[1] == 0 or v2[0] == 0 and v2[1] == 0:
                continue
                
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            det = v1[0]*v2[1] - v1[1]*v2[0]
            angle = math.atan2(det, dot)
            direction_changes.append(angle)
            cross_products.append(det)
        
        if not direction_changes:
            return None
        
        avg_direction_change = sum(direction_changes) / len(direction_changes)
        total_rotation = sum(cross_products)
        
        if abs(avg_direction_change) < curve_threshold:
            return "clockwise" if total_rotation > 0 else "counter-clockwise"
        return None

    def is_pinching(finger_positions):
        #pinching check
        thumb, index, middle = finger_positions
        # Calculate distances between fingers
        dist_thumb_index = math.dist(thumb, index)
        dist_thumb_middle = math.dist(thumb, middle)
        dist_index_middle = math.dist(index, middle)
        
        # All distances must be below threshold
        return (dist_thumb_index < pinch_threshold and 
                dist_thumb_middle < pinch_threshold and 
                dist_index_middle < pinch_threshold)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame = cv2.flip(frame, 1)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Cooldown mechanism
        if cooldown_counter > 0:
            cooldown_counter -= 1
        else:
            swipe_detected = False
            curve_detected = False
            combo_detected = False
            gesture_detected = None
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Track all finger tips
                finger_positions = []
                for id in finger_tip_ids:
                    landmark = hand_landmarks.landmark[id]
                    height, width, _ = image.shape
                    cx, cy = int(landmark.x * width), int(landmark.y * height)
                    finger_positions.append((cx, cy))
                    
                    # Draw finger tips and labels
                    cv2.circle(image, (cx, cy), 10, (0, 255, 0), cv2.FILLED)
                    if id == 4:
                        finger_name = "Thumb"
                    elif id == 8:
                        finger_name = "Index"
                    elif id == 12:
                        finger_name = "Middle"
                    
                    cv2.putText(image, finger_name, (cx-20, cy-20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Check if fingers are pinching
                pinching = is_pinching(finger_positions)
                
                # Only track movement if pinching
                if pinching:
                    # Store average position of all fingers
                    avg_x = sum(p[0] for p in finger_positions) // len(finger_positions)
                    avg_y = sum(p[1] for p in finger_positions) // len(finger_positions)
                    position_history.append((avg_x, avg_y))
                    frame_count += 1
                    
                    # Draw the movement path
                    for i in range(1, len(position_history)):
                        cv2.line(image, position_history[i-1], position_history[i], (255, 0, 0), 2)
                    
                    # Detect gestures after collecting enough frames
                    if frame_count > 5 and len(position_history) > 5:
                        start_x, start_y = position_history[0]
                        end_x, end_y = position_history[-1]
                        
                        dx = end_x - start_x
                        dy = end_y - start_y
                        
                        # Detect swipe if not in cooldown
                        if not swipe_detected and not curve_detected and not combo_detected:
                            if abs(dx) > swipe_threshold and abs(dx) > abs(dy):
                                if dx > 0:
                                    last_swipe = "right"
                                    cv2.putText(image, "SWIPE RIGHT", (50, 50), 
                                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                elif dx < 0:
                                    last_swipe = "left"
                                    cv2.putText(image, "SWIPE LEFT", (50, 50), 
                                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                            
                            elif abs(dy) > swipe_threshold and abs(dy) > abs(dx):
                                if dy > 0:
                                    last_swipe="down"
                                    cv2.putText(image, "SWIPE DOWN", (50, 50), 
                                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                elif dy < 0:
                                    last_swipe="up"
                                    cv2.putText(image, "SWIPE UP", (50, 50), 
                                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        
                        # Detect curve motion
                        if len(position_history) >= min_curve_points:
                            curve = detect_curve(position_history)
                            if curve and not curve_detected and not combo_detected:
                                last_curve = curve
                                cv2.putText(image, f"CURVE: {curve}", (50, 100), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        
                        # Check for combo gestures
                        if last_swipe and last_curve and not combo_detected:
                            #clockwise & down
                            if last_curve == "clockwise" and last_swipe == "down":
                                print("ACCEPTED: Clockwise + down")
                                cv2.putText(image, "ACCEPTED: Clockwise + down", (50, 150), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                combo_detected = True
                                cooldown_counter = cooldown_frames
                                gesture_detected = "Clockwise + down"

                            # Accept clockwise + left swipe
                            if last_curve == "clockwise" and last_swipe == "left":
                                print("ACCEPTED: Clockwise + Left")
                                cv2.putText(image, "ACCEPTED: Clockwise + Left", (50, 150), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                combo_detected = True
                                cooldown_counter = cooldown_frames
                                gesture_detected = "Clockwise + Left"

                            #counterclockwise & up
                            elif last_curve == "counter-clockwise" and last_swipe == "up":
                                print("ACCEPTED: Counter-Clockwise + up")
                                cv2.putText(image, "ACCEPTED: Counter-Clockwise + up", (50, 150), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                combo_detected = True
                                cooldown_counter = cooldown_frames
                                gesture_detected = "Counter-Clockwise + up"

                            # Accept counter-clockwise + right swipe
                            elif last_curve == "counter-clockwise" and last_swipe == "right":
                                print("ACCEPTED: Counter-Clockwise + Right")
                                cv2.putText(image, "ACCEPTED: Counter-Clockwise + Right", (50, 150), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                combo_detected = True
                                cooldown_counter = cooldown_frames
                                gesture_detected = "Counter-Clockwise + Right"
                            
                            # Reset after checking
                            last_swipe = None
                            last_curve = None
                else:
                    # Clear history if not pinching
                    position_history.clear()
                    frame_count = 0
                    last_swipe = None
                    last_curve = None
        else:
            position_history.clear()
            frame_count = 0
            last_swipe = None
            last_curve = None
        
        # Visual feedback for pinching state
        if results.multi_hand_landmarks:
            pinching_status = "PINCHING" if pinching else "NOT PINCHING"
            cv2.putText(image, f"Status: {pinching_status}", (50, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Update the frame to be displayed on the web
        with frame_lock:
            output_frame = image.copy()

    cap.release()

def generate():
    global output_frame, gesture_detected
    while True:
        with frame_lock:
            if output_frame is None:
                continue
            
            # Encode the frame in JPEG format
            (flag, encoded_image) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
            
        # Yield the output frame in byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encoded_image) + b'\r\n')
        time.sleep(0.033)  # ~30 FPS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/gesture")
def get_gesture():
    global gesture_detected
    if gesture_detected:
        response = f"{gesture_detected}"
        return Response(response)
    return Response("No gesture detected")

if __name__ == "__main__":
    # Start a thread that will perform gesture detection
    t = threading.Thread(target=detect_gestures)
    t.daemon = True
    t.start()
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=4999, debug=True, threaded=True, use_reloader=False)