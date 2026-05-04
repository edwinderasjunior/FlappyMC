# Import pygame library for game development and os for file handling
import pygame
import os

# These constants define the screen dimensions, scroll speed, fade speed, frames per second, and the folder containing the images
SCREEN_W, SCREEN_H = 1280, 720 
SCROLL_SPEED = 1.5            # Slow and smooth
FADE_SPEED = 3                 # Higher is faster fade
FPS = 60
IMAGE_FOLDER = "panoramas"

# Create a class to handle the panoramic fading effect
class Panoramicfader:
    # Initialize the class with screen dimensions and set up necessary variables
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 1. Get images from folder
        self.image_list = sorted([
            os.path.join(IMAGE_FOLDER, f) 
            for f in os.listdir(IMAGE_FOLDER) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        # Ensure we have images to work with, otherwise raise an error
        if not self.image_list:
            raise FileNotFoundError(f"No images in '{IMAGE_FOLDER}'")

        # These variables will track the current image index, the x position of the image, the alpha value for fading, and the current state of the animation
        self.index = 0
        self.img_x = 0.0
        self.fade_alpha = 0
        self.state = "SLIDE" # SLIDE, FADE_OUT, FADE_IN
        
        # 2. Setup Fade Overlay using documentation from https://www.pygame.org/docs/ref/surface.html#pygame.Surface.set_alpha
        self.fade_surf = pygame.Surface((screen_w, screen_h))
        self.fade_surf.fill((0, 0, 0))
        
        self.load_image()

    # This method loads the current image, scales it to fit the screen height while maintaining aspect ratio, and calculates the scroll limit for when to start fading out
    def load_image(self):
        current_path = self.image_list[self.index]
        raw_img = pygame.image.load(current_path).convert()
        
        # Scale to screen height
        aspect_ratio = raw_img.get_width() / raw_img.get_height()
        scaled_w = int(self.screen_h * aspect_ratio)
        self.img = pygame.transform.smoothscale(raw_img, (scaled_w, self.screen_h))
        
        self.img_x = 0.0
        # Trigger fade slightly BEFORE the image actually ends to hide the edge
        # We stop when the right edge of the image is 50 pixels from the right of the screen
        self.scroll_limit = -(scaled_w - self.screen_w - 50)

# This method updates the position of the image and the alpha value for fading based on the current state of the animation. It handles the sliding, fading out, and fading in transitions.
    def update(self):
        if self.state == "SLIDE":
            self.img_x -= SCROLL_SPEED
            if self.img_x <= self.scroll_limit:
                self.state = "FADE_OUT"

        elif self.state == "FADE_OUT":
            # Continue sliding slowly while fading for a natural feel
            self.img_x -= (SCROLL_SPEED * 0.2) 
            self.fade_alpha += FADE_SPEED
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                # Cycle to next image or back to 0
                self.index = (self.index + 1) % len(self.image_list)
                self.load_image()
                self.state = "FADE_IN"

        elif self.state == "FADE_IN":
            self.img_x -= SCROLL_SPEED
            self.fade_alpha -= FADE_SPEED
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.state = "SLIDE"

    def draw(self, surface):
        # Draw the panorama
        surface.blit(self.img, (int(self.img_x), 0))
        
        # Draw the black overlay
        if self.fade_alpha > 0:
            self.fade_surf.set_alpha(self.fade_alpha)
            surface.blit(self.fade_surf, (0, 0))


# Main Function

"""
This function initializes the pygame environment, sets up the display, and creates an instance of the Panoramicfader class. 
It then enters the main game loop where it handles events, updates the panoramic fader, and draws the current state to the screen. 
The loop continues until the user quits the application. 
"""
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Smooth Panoramic Loop")
    clock = pygame.time.Clock()

    try:
        slider = Panoramicfader(SCREEN_W, SCREEN_H)
    except Exception as e:
        print(f"Error: {e}")
        return

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        slider.update()
        screen.fill((0, 0, 0))
        slider.draw(screen)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

# This ensures that the main function is called when the script is executed directly, allowing the game to run.
if __name__ == "__main__":
    main()