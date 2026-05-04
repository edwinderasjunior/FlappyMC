# import io is used to handle in-memory byte streams, which allows us to load images directly from the web without saving them to disk first.
import io

# Import sys to handle system-specific parameters and functions, such as exiting the program gracefully in case of errors.
import sys

# Import pygame library for game development and os for file handling
import pygame
import os
import random

# requests library is used to fetch Minecraft skins from the Minotar API, allowing to display player avatars in the game.
import requests

# + ----------------------------- +
# Settings and Constants
# + ----------------------------- +

# Screen Resolution
SCREEN_W, SCREEN_H = 1280, 720

# Background and animation settings
SCROLL_SPEED = 1.5
FADE_SPEED = 3
FPS = 60
IMAGE_FOLDER = "panoramas"

# Set up the music folder path
MUSIC_FOLDER = "assets"

# Parallax settings
GRASS_SPEED = 0.6

# Player head size and block size
PLAYER_HEAD_W, PLAYER_HEAD_H = 80, 80
BLOCK_W, BLOCK_H = 120, 533

# Colors
WHITE, BLACK, GRAY = (255, 255, 255), (0, 0, 0), (50, 50, 50)

# Initialize pygame
pygame.init()

# Initialize the mixer for music and sound effects
pygame.mixer.init()

# + ----------------------------- +
# Classes
# + ----------------------------- +

# Create a class to handle the panoramic fading effect
class PanoramicFader:
    # Initialize the class with screen dimensions and set up necessary variables
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # 1. Get images from folder
        image_paths = sorted([
            os.path.join(IMAGE_FOLDER, f)
            for f in os.listdir(IMAGE_FOLDER)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        if not image_paths:
            raise FileNotFoundError(f"No images in '{IMAGE_FOLDER}'")

        # Preload and scale all images upfront to avoid lag during gameplay
        self.images = []
        for path in image_paths:
            raw = pygame.image.load(path).convert()
            aspect_ratio = raw.get_width() / raw.get_height()
            scaled_w = int(self.screen_h * aspect_ratio)
            img = pygame.transform.smoothscale(raw, (scaled_w, self.screen_h))
            self.images.append(img)

        # Precompute scroll limits for each image
        self.scroll_limits = [
            -(img.get_width() - self.screen_w - 50)
            for img in self.images
        ]

        # These variables will track the current image index, the x position of the image, the alpha value for fading, and the current state of the animation
        self.index = 0
        self.img_x = 0.0
        self.fade_alpha = 0
        self.state = "SLIDE"  # SLIDE, FADE_OUT, FADE_IN

        # 2. Setup Fade Overlay using documentation from https://www.pygame.org/docs/ref/surface.html#pygame.Surface.set_alpha
        self.fade_surf = pygame.Surface((screen_w, screen_h))
        self.fade_surf.fill((0, 0, 0))

        self.load_image()

    # Reset position and scroll limit for the current image
    def load_image(self):
        self.img_x = 0.0
        self.scroll_limit = self.scroll_limits[self.index]

    # This method updates the position of the image and the alpha value for fading based on the current state of the animation
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
                self.index = (self.index + 1) % len(self.images)
                self.load_image()
                self.state = "FADE_IN"

        elif self.state == "FADE_IN":
            self.img_x -= SCROLL_SPEED
            self.fade_alpha -= FADE_SPEED
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.state = "SLIDE"

    def draw(self, surface):
        # Draw the current panorama image
        surface.blit(self.images[self.index], (int(self.img_x), 0))
        # Draw the black fade overlay
        if self.fade_alpha > 0:
            self.fade_surf.set_alpha(self.fade_alpha)
            surface.blit(self.fade_surf, (0, 0))


# Player class to handle player head skin and movement
class Player(pygame.Rect):
    def __init__(self, img):
        super().__init__(SCREEN_W // 8, SCREEN_H // 2, PLAYER_HEAD_W, PLAYER_HEAD_H)
        self.image = img
        # Velocity and gravity for simple physics simulation
        self.velocity = 0
        self.gravity = 0.5

    def update(self):
        self.velocity += self.gravity
        self.y += self.velocity
        self.top = max(0, self.top)   # Prevent the player from going above the screen
        self.bottom = min(SCREEN_H, self.bottom)  # Prevent the player from going below the screen


# Block class to handle the obstacle blocks
class Block(pygame.Rect):
    def __init__(self, x, y, img):
        super().__init__(x, y, BLOCK_W, BLOCK_H)
        self.image = img


# + ----------------------------- +
# Functions
# + ----------------------------- +

# This function loads random music every time the game starts
def load_random_music():
    track = f"music{str(random.randint(1, 34)).zfill(2)}.mp3"
    path = os.path.join(MUSIC_FOLDER, track)
    if os.path.exists(path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1)


# This function loads a Minecraft skin from the Minotar API www.minotar.net
def get_minecraft_skin(username):
    url = f"https://minotar.net/avatar/{username}/{PLAYER_HEAD_W}"
    # Use requests package to fetch the image data and load it into pygame
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return pygame.image.load(io.BytesIO(response.content)).convert_alpha()
    except:
        return None


# This function draws the panorama background and scrolling grass on top
def draw_background(scroll, panorama, grass, window):
    if panorama:
        panorama.draw(window)
    else:
        window.fill(BLACK)
    grass_x = int(scroll * GRASS_SPEED) % SCREEN_W
    # Blitting two grass images to create a seamless scrolling effect
    window.blit(grass, (-grass_x, 0))
    window.blit(grass, (SCREEN_W - grass_x, 0))


# + ----------------------------- +
# Main Function
# + ----------------------------- +

"""
This function initializes the pygame environment, sets up the display, and runs the main game loop.
It handles the username entry screen, gameplay, collisions, and rendering.
"""
def main():
    global window, clock, font

    window = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("FlappyMC - Minecraft-themed Flappy Bird")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 40, bold=True)

    # Load random music at the start of the game
    load_random_music()

    # Load assets here so display exists first
    try:
        grass = pygame.image.load("assets/grass_block.png").convert_alpha()
        grass = pygame.transform.scale(grass, (SCREEN_W, SCREEN_H))
    except Exception as e:
        print(f"grass error: {e}")
        grass = pygame.Surface((SCREEN_W, SCREEN_H))
        grass.fill((0, 50, 0))

    try:
        pipe_img = pygame.image.load("assets/topblock.png").convert_alpha()
        pipe_img = pygame.transform.scale(pipe_img, (BLOCK_W, BLOCK_H))
    except Exception as e:
        print(f"topblock error: {e}")
        pipe_img = pygame.Surface((BLOCK_W, BLOCK_H))
        pipe_img.fill((0, 200, 0))

    try:
        pipe_bottom_img = pygame.image.load("assets/bottomblock.png").convert_alpha()
        pipe_bottom_img = pygame.transform.scale(pipe_bottom_img, (BLOCK_W, BLOCK_H))
    except Exception as e:
        print(f"bottomblock error: {e}")
        pipe_bottom_img = pygame.transform.flip(pipe_img, False, True)

    try:
        panorama = PanoramicFader(SCREEN_W, SCREEN_H)
    except Exception as e:
        print(f"Panorama error: {e}")
        panorama = None

    # Load XP sound effect, but don't crash if it's missing since it's not essential for gameplay
    try:
        xp_sound = pygame.mixer.Sound("assets/xp.mp3")
        # Set a lower volume for the XP sound effect
        xp_sound.set_volume(0.3)
    except Exception as e:
        print(f"xp_sound error: {e}")
        xp_sound = None

    # Load jump sound effect
    try:
        jump_sound = pygame.mixer.Sound("assets/jump.mp3")
        jump_sound.set_volume(0.5)
    except Exception as e:
        print(f"jump_sound error: {e}")
        jump_sound = None

    blocks, scroll, user_text = [], 0, ""
    input_active, game_active, player = True, False, None
    create_block_timer = pygame.USEREVENT + 1

    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Process input specifically for the username screen
            if input_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if user_text.strip() != "":
                            skin = get_minecraft_skin(user_text) or pygame.Surface((PLAYER_HEAD_W, PLAYER_HEAD_H))
                            player = Player(skin)
                            input_active, game_active = False, True
                            pygame.time.set_timer(create_block_timer, 2500)
                    elif event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    else:
                        if event.unicode.isprintable():
                            user_text += event.unicode

            # Process input specifically for gameplay
            elif game_active:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    player.velocity = -9
                    if jump_sound:
                        jump_sound.play()
                if event.type == create_block_timer:
                    gap_y = random.randint(100, SCREEN_H - 300)
                    blocks.append(Block(SCREEN_W, gap_y - BLOCK_H, pipe_img))
                    blocks.append(Block(SCREEN_W, gap_y + 300, pipe_bottom_img))

        # Always update panorama so it keeps animating on both screens
        if panorama:
            panorama.update()

        if input_active:
            if panorama:
                panorama.draw(window)
            else:
                window.fill(BLACK)

            prompt = font.render("Enter Minecraft Username:", True, WHITE)
            window.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, 200))
            input_box = pygame.Rect(SCREEN_W // 2 - 250, 300, 500, 55)
            pygame.draw.rect(window, GRAY, input_box)
            text_surf = font.render(user_text, True, WHITE)
            window.blit(text_surf, (input_box.x + 15, input_box.y + 8))

        elif game_active:
            scroll += 3
            player.update()

            # b represents each block in the blocks list
            # We check if it has passed the player to play the XP sound effect
            # We also check for collisions between the player and the blocks which would end the game
            for b in blocks[:]:
                b.x -= 5
                if b.right < 0:
                    blocks.remove(b)
                if player.colliderect(b):
                    game_active, input_active, blocks, scroll, user_text = False, True, [], 0, ""
                if b.right < player.left and not getattr(b, 'scored', False):
                    b.scored = True
                    if xp_sound:
                        xp_sound.play()

            # Rendering — panorama → grass → blocks → player
            draw_background(scroll, panorama, grass, window)
            for b in blocks:
                window.blit(b.image, b)
            window.blit(player.image, player)

        pygame.display.update()
        clock.tick(FPS)


# This ensures that the main function is called when the script is executed directly, allowing the game to run.
if __name__ == "__main__":
    main()