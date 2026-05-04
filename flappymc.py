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

"""

These settings and constants define the screen resolution, background and animation settings, 
parallax scrolling speed, player head size, block size, and colors used in the game.

"""

# Screen Resolution
SCREEN_W, SCREEN_H = 1280, 720

# Background and animation settings
SCROLL_SPEED = 1.5
GAME_SPEED = 5 # Speed for pipes and grass
FADE_SPEED = 4
FPS = 60
IMAGE_FOLDER = "panoramas"

# Set up the music folder path
MUSIC_FOLDER = "assets"

# Parallax settings
GRASS_SPEED = 1.0

# Player head size and block size
PLAYER_HEAD_W, PLAYER_HEAD_H = 80, 80
BLOCK_W, BLOCK_H = 120, 800

# Colors
WHITE, BLACK, GRAY = (255, 255, 255), (0, 0, 0), (50, 50, 50)
RED = (255, 50, 50)

# Initialize pygame
pygame.init()

# Initialize the mixer for music and sound effects
pygame.mixer.init()

# + ----------------------------- +
# Classes
# + ----------------------------- +

"""

These classes handle the panoramic fading effect, player head skin and movement, and the obstacle blocks in the game.

"""


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
        # use original_image as a reference so quality doesn't change during rotation
        self.original_image = img
        self.image = img
        # Velocity and gravity for simple physics simulation
        self.velocity = 0
        self.gravity = 0.5

    def update(self):
        # Apply gravity and move
        self.velocity += self.gravity
        self.y += self.velocity
        
        # Prevent the player from going off-screen (Top only, bottom hits the floor)
        self.top = max(0, self.top)

        # Rotation: Calculate tilt based on velocity
        # pygame.transform.rotate(source_image, angle) from documentation: https://www.pygame.org/docs/ref/transform.html#pygame.transform.rotate
        rotation_angle = self.velocity * -2
        
        # Hold the rotation so the head doesn't do full backflips
        if rotation_angle > 20: rotation_angle = 20    # Max tilt up
        if rotation_angle < -40: rotation_angle = -40  # Max tilt down
        
        # Create the new rotated image from the original
        self.image = pygame.transform.rotate(self.original_image, rotation_angle)


# Block class to handle the obstacle blocks
class Block(pygame.Rect):
    # Added mob_img as an optional parameter (defaults to None)
    def __init__(self, x, y, img, mob_img=None):
        super().__init__(x, y, BLOCK_W, BLOCK_H)
        self.image = img
        self.mob_image = mob_img # Store the animal image
        self.scored = False


# + ----------------------------- +
# Functions
# + ----------------------------- +

"""
These functions handle various aspects of the game, such as loading random music, fetching Minecraft skins, 
drawing the background with parallax scrolling, and managing the main game loop.
"""

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


# This function draws the panorama background
def draw_background(panorama, window):
    if panorama:
        panorama.draw(window)
    else:
        window.fill(BLACK)


# + ----------------------------- +
# Main
# + ----------------------------- +

"""

The main function initializes the pygame environment, sets up the display, and runs the main game loop.
It handles user input for both the username entry screen and the gameplay, updates the game state, and renders all the visual elements on the screen.

"""
def main():
    global window, clock, font

    window = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("FlappyMC - Minecraft-themed Flappy Bird")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 40, bold=True)
    title_font = pygame.font.SysFont("Arial", 60, bold=True)

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

        # Load Mob Images (animal1.png through animal10.png)
        mob_images = []
    
        # Loop from 1 to 10
    for i in range(1, 11):
        filename = f"animal{i}.png"
        try:
            # Load the image from the assets folder
            mob_img = pygame.image.load(f"assets/{filename}").convert_alpha()
            # Scale them to fit exactly in your 120x120 transparent cutout
            mob_img = pygame.transform.scale(mob_img, (120, 120))
            mob_images.append(mob_img)
        except Exception as e:
            # If a file is missing (e.g., you only have 5 animals so far), it just prints a warning and skips it!
            print(f"Could not load {filename}: {e}")

    try:
        panorama = PanoramicFader(SCREEN_W, SCREEN_H)
    except Exception as e:
        print(f"Panorama error: {e}")
        panorama = None

    # Load XP sound effect, but don't crash if it's missing since it's not essential for gameplay
    try:
        xp_sound = pygame.mixer.Sound("assets/xp.wav")
        # Set a lower volume for the XP sound effect
        xp_sound.set_volume(0.3)
    except Exception as e:
        print(f"xp_sound error: {e}")
        xp_sound = None

    # Load jump sound effect
    try:
        jump_sound = pygame.mixer.Sound("assets/jump.wav")
        jump_sound.set_volume(0.5)
    except Exception as e:
        print(f"jump_sound error: {e}")
        jump_sound = None

    blocks, scroll, user_text = [], 0, ""
    score = 0
    input_active = True
    menu_active = False
    game_active = False
    game_over_active = False
    player = None

    create_block_timer = pygame.USEREVENT + 1

    # Menu Buttons
    btn_w, btn_h = 250, 60
    btn_x = SCREEN_W // 2 - btn_w // 2
    play_button = pygame.Rect(btn_x, 300, btn_w, btn_h)
    options_button = pygame.Rect(btn_x, 380, btn_w, btn_h)
    
    # Game Over Buttons
    reset_button = pygame.Rect(btn_x, 350, btn_w, btn_h)
    exit_button = pygame.Rect(btn_x, 430, btn_w, btn_h)

    while True:
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()
        
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
                            input_active = False
                            menu_active = True
                    elif event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    else:
                        if event.unicode.isprintable():
                            user_text += event.unicode

            # Process input specifically for main menu
            elif menu_active:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_button.collidepoint(event.pos):
                        menu_active = False
                        game_active = True
                        pygame.time.set_timer(create_block_timer, 1500)
                    if options_button.collidepoint(event.pos):
                        print("Options clicked! (Implement settings here)")

            # Process input specifically for gameplay
            elif game_active:
                # Support BOTH Spacebar and Left Mouse Click to jump
                if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or \
                   (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    player.velocity = -9
                    if jump_sound:
                        jump_sound.play()
                        
                if event.type == create_block_timer:
                    gap_y = random.randint(150, SCREEN_H - 400)
                    
                    # 1. Top Pipe (No mob)
                    blocks.append(Block(SCREEN_W, gap_y - BLOCK_H, pipe_img))
                    
                    # 2. Bottom Pipe (With random mob)
                    # Pick a random mob if the list isn't empty, otherwise None
                    chosen_mob = random.choice(mob_images) if mob_images else None
                    
                    blocks.append(Block(SCREEN_W, gap_y + 250, pipe_bottom_img, mob_img=chosen_mob))

            # Process input specifically for Game Over screen
            elif game_over_active:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if reset_button.collidepoint(event.pos):
                        blocks = []
                        scroll = 0
                        score = 0
                        player.y = SCREEN_H // 2
                        player.velocity = 0
                        game_over_active = False
                        game_active = True
                        pygame.time.set_timer(create_block_timer, 1500)
                    if exit_button.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()

        # Always update panorama so it keeps animating on both screens
        if panorama:
            panorama.update()

        if game_active:
            scroll += GAME_SPEED
            player.update()

            # b represents each block in the blocks list
            for b in blocks[:]:
                b.x -= GAME_SPEED
                if b.right < 0:
                    blocks.remove(b)
                
                # We also check for collisions between the player and the blocks which would end the game
                if player.colliderect(b):
                    game_active = False
                    game_over_active = True
                
                # We check if it has passed the player to play the XP sound effect and get the score
                if b.right < player.left and not getattr(b, 'scored', False):
                    b.scored = True
                    if b.y < 0:
                        score +=1
                        if xp_sound:
                            xp_sound.play()

            # Floor Collision (Checks bottom of screen since grass is scaled to full screen)
            if player.bottom > SCREEN_H:
                player.bottom = SCREEN_H
                game_active = False
                game_over_active = True

        # Rendering — Panorama is drawn first, then blocks, then grass, and finally the player on top of everything else
        draw_background(panorama, window)

        if input_active:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H))
            overlay.set_alpha(150)
            window.blit(overlay, (0,0))
            prompt = font.render("Enter Minecraft Username:", True, WHITE)
            window.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, 200))
            input_box = pygame.Rect(SCREEN_W // 2 - 250, 300, 500, 55)
            pygame.draw.rect(window, GRAY, input_box)
            text_surf = font.render(user_text, True, WHITE)
            window.blit(text_surf, (input_box.x + 15, input_box.y + 8))

        elif menu_active:
            title = title_font.render("FLAPPY MC", True, WHITE)
            window.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 150))
            
            pygame.draw.rect(window, WHITE if play_button.collidepoint(mouse_pos) else GRAY, play_button)
            play_text = font.render("PLAY", True, BLACK if play_button.collidepoint(mouse_pos) else WHITE)
            window.blit(play_text, (play_button.x + 75, play_button.y + 7))

            pygame.draw.rect(window, WHITE if options_button.collidepoint(mouse_pos) else GRAY, options_button)
            opt_text = font.render("OPTIONS", True, BLACK if options_button.collidepoint(mouse_pos) else WHITE)
            window.blit(opt_text, (options_button.x + 40, options_button.y + 7))

        elif game_active or game_over_active:
            # Draw blocks and mobs
            for b in blocks:
                # 1. Draw the main pipe
                window.blit(b.image, b.topleft)
                
                # 2. If this block has an animal, draw it in the exact same spot!
                # Because the top 120px of the pipe are transparent, it will fit perfectly.
                if b.mob_image:
                    window.blit(b.mob_image, b.topleft)

            # Draw grass (Drawn at Y = 0 because it fills the whole screen)
            grass_x = int(scroll * GRASS_SPEED) % SCREEN_W
            window.blit(grass, (-grass_x, 0))
            window.blit(grass, (SCREEN_W - grass_x, 0))

            # Draw player on top of everything else 
            window.blit(player.image, player.topleft)

            if game_active:
                score_str = str(score)
                s_text = title_font.render(score_str, True, WHITE)
                sh_text = title_font.render(score_str, True, BLACK)
                text_x = SCREEN_W // 2 - s_text.get_width() // 2
                window.blit(sh_text, (text_x + 4, 54))
                window.blit(s_text, (text_x, 50))

            if game_over_active:
                overlay = pygame.Surface((SCREEN_W, SCREEN_H))
                overlay.set_alpha(150)
                overlay.fill(BLACK)
                window.blit(overlay, (0, 0))

                go_text = title_font.render("YOU DIED", True, RED)
                window.blit(go_text, (SCREEN_W // 2 - go_text.get_width() // 2, 150))
                
                final_score = font.render(f"Score: {score}", True, WHITE)
                window.blit(final_score, (SCREEN_W // 2 - final_score.get_width() // 2, 240))

                pygame.draw.rect(window, WHITE if reset_button.collidepoint(mouse_pos) else GRAY, reset_button)
                reset_text = font.render("PLAY AGAIN", True, BLACK if reset_button.collidepoint(mouse_pos) else WHITE)
                window.blit(reset_text, (reset_button.x + 20, reset_button.y + 7))

                pygame.draw.rect(window, WHITE if exit_button.collidepoint(mouse_pos) else GRAY, exit_button)
                exit_text = font.render("QUIT", True, BLACK if exit_button.collidepoint(mouse_pos) else WHITE)
                window.blit(exit_text, (exit_button.x + 85, exit_button.y + 7))

        pygame.display.update()
        clock.tick(FPS)

# This ensures that the main function is called when the script is executed directly, allowing the game to run.
if __name__ == "__main__":
    main()