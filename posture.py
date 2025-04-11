import cv2
import mediapipe as mp
import math
import time

# -------------------- THRESHOLD VARIABLES --------------------
HEAD_THRESHOLD_OFFSET = 10       # pixels: if current head height exceeds baseline + this, head is bending
BACK_BEND_THRESHOLD = 3         # degrees: acceptable trunk angle is within ±BACK_BEND_THRESHOLD of 180°
# -------------------------------------------------------------

mp_pose = mp.solutions.pose  # type: ignore[attr-defined]
mp_drawing = mp.solutions.drawing_utils  # type: ignore[attr-defined]

def calculate_angle(a, b, c):
    """
    Calculate the angle between three points using only their x and y coordinates.
    Returns an angle in 0-360°.
    """
    a_xy = (a.x, a.y)
    b_xy = (b.x, b.y)
    c_xy = (c.x, c.y)
    angle = math.degrees(math.atan2(c_xy[1] - b_xy[1], c_xy[0] - b_xy[0]) -
                         math.atan2(a_xy[1] - b_xy[1], a_xy[0] - b_xy[0]))
    if angle < 0:
        angle += 360
    return angle

# Open the external camera (adjust index if needed)
cap = cv2.VideoCapture(0)

# Calibration variable for head height.
start_time = time.time()
baseline_head_height = None

with mp_pose.Pose(min_detection_confidence=0.5,
                   min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Flip frame horizontally for a mirrored view.
        frame = cv2.flip(frame, 1)
        
        # Convert image from BGR to RGB for processing.
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        
        # Process image to detect pose landmarks.
        results = pose.process(image)
        
        # Convert image back to BGR for rendering.
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Default labels.
        posture = "Front Posture Detected"
        trunk_info = ""
        head_info = ""
        overall_posture = "Good Posture"
        
        if results.pose_landmarks:
            # Draw pose landmarks.
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            landmarks = results.pose_landmarks.landmark
            
            # Retrieve key landmarks (using only x and y).
            left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
            left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
            right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
            nose = landmarks[mp_pose.PoseLandmark.NOSE.value]
            
            # Calculate side angles.
            left_angle = calculate_angle(left_elbow, left_shoulder, left_hip)
            right_angle = calculate_angle(right_elbow, right_shoulder, right_hip)
            cv2.putText(image, f'Left Angle: {int(left_angle)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(image, f'Right Angle: {int(right_angle)}', (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Determine if turned (side posture).
            shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2
            if abs(left_angle - right_angle) > 30 or abs(nose.x - shoulder_mid_x) > 0.05:
                posture = "Side Posture Detected"
            
            # Calculate trunk (back) angle using only x and y if key landmarks are detected.
            if (left_shoulder.visibility > 0.5 and right_shoulder.visibility > 0.5 and
                left_hip.visibility > 0.5 and right_hip.visibility > 0.5):
                
                mid_shoulder = ((left_shoulder.x + right_shoulder.x) / 2,
                                (left_shoulder.y + right_shoulder.y) / 2)
                mid_hip = ((left_hip.x + right_hip.x) / 2,
                           (left_hip.y + right_hip.y) / 2)
                trunk_angle = math.degrees(math.atan2(
                    mid_shoulder[0] - mid_hip[0],
                    mid_shoulder[1] - mid_hip[1]))
                if trunk_angle < 0:
                    trunk_angle += 360
                trunk_info = f'Back Angle: {int(trunk_angle)}°'
                
                # Evaluate trunk angle relative to 180° ± BACK_BEND_THRESHOLD.
                if trunk_angle < (180 - BACK_BEND_THRESHOLD):
                    # Back is bending (angle too low)
                    overall_posture = "Bad Posture"
                    trunk_info += " (Bending)"
                elif trunk_angle > (180 + BACK_BEND_THRESHOLD):
                    # User is resting; ignore head height.
                    overall_posture = "Good Posture"
                else:
                    # Trunk angle within acceptable range; now check head height.
                    image_height = image.shape[0]
                    current_head_height = nose.y * image_height
                    head_info = f'Head Height: {int(current_head_height)} px'
                    
                    current_time = time.time()
                    # Calibration: record baseline head height after 5 seconds.
                    if current_time - start_time > 5 and baseline_head_height is None:
                        baseline_head_height = current_head_height
                    
                    if baseline_head_height is not None:
                        cv2.putText(image, f'Baseline Head: {int(baseline_head_height)} px', (10, 190),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 0), 2)
                        head_bending = current_head_height > baseline_head_height + HEAD_THRESHOLD_OFFSET
                        if head_bending:
                            head_info += " (Bending)"
                            overall_posture = "Bad Posture"
                        else:
                            overall_posture = "Good Posture"
            else:
                trunk_info = "Back not detected"
                head_info = "Head not detected"
            
            # Display overall posture and measurements.
            cv2.putText(image, overall_posture, (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(image, trunk_info, (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            cv2.putText(image, head_info, (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        cv2.imshow('Posture Detection', image)
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()