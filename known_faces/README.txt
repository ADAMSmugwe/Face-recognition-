KNOWN FACES DIRECTORY
====================

This directory should contain images of people you want the system to recognize.

NAMING CONVENTION:
- Name your image files with the person's name
- Use underscores or dashes instead of spaces
- Examples:
  * john_doe.jpg
  * jane-smith.png
  * alice_cooper.jpeg
  * bob_wilson.jpg

SUPPORTED FORMATS:
- .jpg, .jpeg
- .png
- .bmp
- .tiff, .tif

IMAGE REQUIREMENTS:
- Clear, well-lit photos
- Face should be clearly visible
- Front-facing photos work best
- One person per image (if multiple faces, first detected face will be used)
- Recommended resolution: 300x300 pixels or larger

TIPS FOR BEST RESULTS:
- Use high-quality images
- Ensure good lighting
- Avoid sunglasses or face coverings
- Multiple images per person can improve accuracy
- Use recent photos for best recognition

EXAMPLE STRUCTURE:
known_faces/
├── john_doe.jpg
├── jane_smith.png
├── alice_cooper_1.jpg
├── alice_cooper_2.jpg
└── bob_wilson.jpeg

After adding images, run:
python encode_faces.py

This will process all images and create the encodings file needed for recognition.
