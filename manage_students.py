#!/usr/bin/env python3
"""
Student Management Script for Face Recognition System

This script provides an interactive menu to manage student records:
- Add new students with face images
- Delete existing students
- Rename students
- View all students
- Re-encode all faces

Usage:
    python manage_students.py
"""

import os
import sys
import pickle
import shutil
from pathlib import Path
import cv2
import numpy as np

try:
    import face_recognition
except ImportError:
    print("Error: face_recognition library not installed")
    print("Please install: pip install face-recognition")
    sys.exit(1)


class StudentManager:
    """Manages student data for the face recognition system."""
    
    def __init__(self, images_dir="images", encodings_file="encodings/known_faces.pkl"):
        self.images_dir = Path(images_dir)
        self.encodings_file = Path(encodings_file)
        self.images_dir.mkdir(exist_ok=True)
        self.encodings_file.parent.mkdir(exist_ok=True)
    
    def list_students(self):
        """List all students with their image counts."""
        students = {}
        
        if not self.images_dir.exists():
            return students
        
        # Count images for each student
        for person_dir in self.images_dir.iterdir():
            if person_dir.is_dir():
                image_files = list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.png")) + list(person_dir.glob("*.jpeg"))
                students[person_dir.name] = len(image_files)
        
        return students
    
    def display_students(self):
        """Display all students in a formatted list."""
        students = self.list_students()
        
        if not students:
            print("\n❌ No students found in the system.")
            return False
        
        print("\n" + "=" * 50)
        print("📋 CURRENT STUDENTS")
        print("=" * 50)
        for idx, (name, count) in enumerate(sorted(students.items()), 1):
            print(f"{idx}. {name:<30} ({count} image{'s' if count != 1 else ''})")
        print("=" * 50)
        return True
    
    def add_student(self):
        """Add a new student with webcam capture or existing images."""
        print("\n" + "=" * 50)
        print("➕ ADD NEW STUDENT")
        print("=" * 50)
        
        # Get student name
        while True:
            name = input("\nEnter student name (or 'cancel' to go back): ").strip()
            if name.lower() == 'cancel':
                return
            
            if not name:
                print("❌ Name cannot be empty!")
                continue
            
            # Check if student already exists
            student_dir = self.images_dir / name
            if student_dir.exists():
                print(f"⚠️  Student '{name}' already exists!")
                choice = input("Do you want to add more images to this student? (y/n): ").lower()
                if choice != 'y':
                    continue
            else:
                student_dir.mkdir(exist_ok=True)
            
            break
        
        # Choose input method
        print("\nHow would you like to add images?")
        print("1. Capture from webcam")
        print("2. Copy from existing folder")
        choice = input("Enter choice (1/2): ").strip()
        
        if choice == '1':
            self._capture_from_webcam(student_dir, name)
        elif choice == '2':
            self._copy_from_folder(student_dir, name)
        else:
            print("❌ Invalid choice!")
    
    def _capture_from_webcam(self, student_dir, name):
        """Capture images from webcam with SMART GUIDANCE."""
        print("\n📷 Starting SMART webcam capture...")
        print("🎯 SMART GUIDANCE enabled - I'll tell you:")
        print("  ✅ When lighting is perfect")
        print("  ⚠️  If it's too dark")
        print("  ⚠️  If face not detected")
        print("  ⚠️  If you need to move closer/back")
        print("\nPress SPACE when status is '✅ PERFECT!', 'q' when done (3-5 images recommended)\n")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open webcam!")
            return
        
        image_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to capture frame")
                    break
                
                # Make display copy
                display_frame = frame.copy()
                height, width = display_frame.shape[:2]
                
                # Convert to grayscale for analysis
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray)
                
                # Detect faces using face_recognition
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                
                # Analyze and give feedback
                feedback = ""
                feedback_color = (0, 0, 255)  # Red by default
                status = "❌"
                
                if brightness < 60:
                    feedback = "⚠️  TOO DARK - Turn on lights!"
                    feedback_color = (0, 165, 255)  # Orange
                elif len(face_locations) == 0:
                    feedback = "❌ NO FACE - Look at camera"
                    feedback_color = (0, 0, 255)  # Red
                elif len(face_locations) > 1:
                    feedback = "⚠️  MULTIPLE FACES - Only one"
                    feedback_color = (0, 165, 255)  # Orange
                else:
                    # One face detected - (top, right, bottom, left)
                    top, right, bottom, left = face_locations[0]
                    w = right - left
                    h = bottom - top
                    face_size = w * h
                    frame_size = width * height
                    face_ratio = face_size / frame_size
                    
                    # Draw rectangle
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                    
                    if face_ratio < 0.05:
                        feedback = "⚠️  MOVE CLOSER"
                        feedback_color = (0, 165, 255)
                    elif face_ratio > 0.4:
                        feedback = "⚠️  MOVE BACK"
                        feedback_color = (0, 165, 255)
                    elif brightness < 80:
                        feedback = "⚠️  A BIT DARK"
                        feedback_color = (0, 200, 255)
                    else:
                        feedback = "✅ PERFECT! Press SPACE"
                        feedback_color = (0, 255, 0)  # Green
                        status = "✅"
                
                # Display feedback - BIG AND PROMINENT
                cv2.rectangle(display_frame, (10, 10), (width - 10, 120), (0, 0, 0), -1)
                cv2.rectangle(display_frame, (10, 10), (width - 10, 120), feedback_color, 3)
                cv2.putText(display_frame, feedback, (20, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, feedback_color, 3)
                
                # Instructions
                cv2.putText(display_frame, f"Capturing: {name} | Images: {image_count}", 
                           (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Bottom stats
                cv2.putText(display_frame, f"Brightness: {int(brightness)}/255", 
                           (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                cv2.imshow(f'Smart Capture: {name}', display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):  # Space bar
                    if status == "✅":
                        filename = student_dir / f"{name}_{image_count + 1:03d}.jpg"
                        cv2.imwrite(str(filename), frame)
                        image_count += 1
                        print(f"✅ Captured GOOD image {image_count}: {filename.name}")
                    else:
                        print(f"❌ Can't capture - {feedback}")
                
                elif key == ord('q'):
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        if image_count > 0:
            print(f"\n✅ Successfully captured {image_count} images for {name}")
            print("🔄 Run option 5 to re-encode all faces.")
        else:
            print("\n⚠️  No images were captured!")
    
    def _copy_from_folder(self, student_dir, name):
        """Copy images from an existing folder."""
        source_folder = input("\nEnter the full path to the folder containing images: ").strip()
        source_path = Path(source_folder)
        
        if not source_path.exists():
            print(f"❌ Folder '{source_folder}' does not exist!")
            return
        
        # Find image files
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []
        for ext in image_extensions:
            image_files.extend(source_path.glob(ext))
        
        if not image_files:
            print("❌ No image files found in the folder!")
            return
        
        print(f"\nFound {len(image_files)} image(s). Copying...")
        
        for idx, img_file in enumerate(image_files, 1):
            dest_file = student_dir / f"{name}_{idx:03d}{img_file.suffix}"
            shutil.copy2(img_file, dest_file)
            print(f"✓ Copied: {img_file.name} -> {dest_file.name}")
        
        print(f"\n✅ Successfully copied {len(image_files)} images for {name}")
        print("🔄 Run option 5 to re-encode all faces.")
    
    def delete_student(self):
        """Delete a student and their images."""
        if not self.display_students():
            return
        
        name = input("\nEnter the exact name of student to delete (or 'cancel'): ").strip()
        if name.lower() == 'cancel':
            return
        
        student_dir = self.images_dir / name
        if not student_dir.exists():
            print(f"❌ Student '{name}' not found!")
            return
        
        # Confirm deletion
        confirm = input(f"⚠️  Are you sure you want to delete '{name}'? This cannot be undone! (yes/no): ").lower()
        if confirm != 'yes':
            print("❌ Deletion cancelled.")
            return
        
        # Delete the directory
        shutil.rmtree(student_dir)
        print(f"✅ Student '{name}' has been deleted.")
        print("🔄 Run option 5 to re-encode all faces.")
    
    def rename_student(self):
        """Rename a student."""
        if not self.display_students():
            return
        
        old_name = input("\nEnter the current name of student (or 'cancel'): ").strip()
        if old_name.lower() == 'cancel':
            return
        
        old_dir = self.images_dir / old_name
        if not old_dir.exists():
            print(f"❌ Student '{old_name}' not found!")
            return
        
        new_name = input(f"Enter new name for '{old_name}': ").strip()
        if not new_name:
            print("❌ New name cannot be empty!")
            return
        
        new_dir = self.images_dir / new_name
        if new_dir.exists():
            print(f"❌ Student '{new_name}' already exists!")
            return
        
        # Rename directory
        old_dir.rename(new_dir)
        
        # Rename image files
        for img_file in new_dir.iterdir():
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                # Extract number from filename
                parts = img_file.stem.split('_')
                if len(parts) > 1 and parts[-1].isdigit():
                    number = parts[-1]
                    new_filename = f"{new_name}_{number}{img_file.suffix}"
                else:
                    new_filename = f"{new_name}{img_file.suffix}"
                
                img_file.rename(new_dir / new_filename)
        
        print(f"✅ Student renamed from '{old_name}' to '{new_name}'")
        print("🔄 Run option 5 to re-encode all faces.")
    
    def reencode_all_faces(self):
        """Re-encode all faces from the images directory."""
        print("\n🔄 Re-encoding all faces...")
        
        # Import encode_faces functionality
        from encode_faces import encode_all_faces
        
        success = encode_all_faces(str(self.images_dir), str(self.encodings_file))
        
        if success:
            print("✅ All faces have been re-encoded successfully!")
        else:
            print("❌ Failed to encode faces. Check the images directory.")


def display_menu():
    """Display the main menu."""
    print("\n" + "=" * 50)
    print("🎓 STUDENT MANAGEMENT SYSTEM")
    print("=" * 50)
    print("1. 📋 View all students")
    print("2. ➕ Add new student")
    print("3. 🗑️  Delete student")
    print("4. ✏️  Rename student")
    print("5. 🔄 Re-encode all faces")
    print("6. 🎥 Run face recognition")
    print("7. 🚪 Exit")
    print("=" * 50)


def main():
    """Main function to run the student management system."""
    manager = StudentManager()
    
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            manager.display_students()
        
        elif choice == '2':
            manager.add_student()
        
        elif choice == '3':
            manager.delete_student()
        
        elif choice == '4':
            manager.rename_student()
        
        elif choice == '5':
            manager.reencode_all_faces()
        
        elif choice == '6':
            print("\n🎥 Starting face recognition...")
            print("This will launch the recognition system in a new process.")
            os.system('python recognize.py')
        
        elif choice == '7':
            print("\n👋 Goodbye!")
            sys.exit(0)
        
        else:
            print("\n❌ Invalid choice! Please enter a number between 1-7.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
