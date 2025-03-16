import random
import time
import math
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from src.utils.logger import get_default_logger

# Get logger
logger = get_default_logger()

class HumanBehaviorSimulator:
    """
    Simulates human-like behavior in the browser to avoid detection.
    Includes realistic mouse movements, scrolling patterns, and timing.
    """
    
    def __init__(self, browser):
        """
        Initialize the simulator with a browser instance.
        
        Args:
            browser: The Selenium WebDriver instance
        """
        self.browser = browser
    
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """
        Sleep for a random amount of time between min and max seconds.
        
        Args:
            min_seconds: Minimum sleep time in seconds
            max_seconds: Maximum sleep time in seconds
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)
    
    def move_mouse_to_element(self, element, direct=False):
        """
        Move the mouse to an element with human-like motion.
        
        Args:
            element: The target element
            direct: If True, move directly to element; otherwise, use curved motion
        """
        try:
            actions = ActionChains(self.browser)
            
            if direct:
                # Direct movement
                actions.move_to_element(element)
                actions.perform()
            else:
                # Get element location
                element_location = element.location
                
                # Get current mouse position (approximated as viewport center)
                viewport_width = self.browser.execute_script("return window.innerWidth")
                viewport_height = self.browser.execute_script("return window.innerHeight")
                current_x = viewport_width / 2
                current_y = viewport_height / 2
                
                # Calculate target coordinates
                target_x = element_location['x']
                target_y = element_location['y']
                
                # Generate a curved path with multiple points
                points = self._generate_curve_points(
                    current_x, current_y, target_x, target_y, 
                    control_points=random.randint(2, 5)
                )
                
                # Move through the points with varying speed
                for point in points:
                    actions.move_by_offset(point[0] - current_x, point[1] - current_y)
                    current_x, current_y = point[0], point[1]
                    
                    # Randomize the pause between movements
                    actions.pause(random.uniform(0.01, 0.1))
                
                actions.perform()
                
            # Add a small pause after reaching the element
            self.random_sleep(0.1, 0.3)
            
        except WebDriverException as e:
            logger.debug(f"Error moving mouse to element: {e}")
    
    def _generate_curve_points(self, start_x, start_y, end_x, end_y, control_points=3):
        """
        Generate points along a curved path using Bezier curves.
        
        Args:
            start_x, start_y: Starting coordinates
            end_x, end_y: Ending coordinates
            control_points: Number of control points for the curve
            
        Returns:
            List of (x, y) coordinates along the curve
        """
        # Create control points with some randomness
        controls = []
        for i in range(control_points):
            progress = (i + 1) / (control_points + 1)
            # Linear interpolation with random offset
            control_x = start_x + progress * (end_x - start_x) + random.uniform(-100, 100)
            control_y = start_y + progress * (end_y - start_y) + random.uniform(-100, 100)
            controls.append((control_x, control_y))
        
        # Generate points along the curve
        points = []
        steps = random.randint(10, 20)  # Number of points to generate
        
        for i in range(steps + 1):
            t = i / steps
            
            # Start with the starting point
            x = start_x
            y = start_y
            
            # Apply Bezier curve formula
            for j, control in enumerate(controls):
                binomial = math.comb(control_points, j+1)
                t_power = t ** (j+1)
                one_minus_t_power = (1 - t) ** (control_points - (j+1))
                
                x += binomial * t_power * one_minus_t_power * (control[0] - x)
                y += binomial * t_power * one_minus_t_power * (control[1] - y)
            
            # Add the influence of the end point
            x += t ** (control_points + 1) * (end_x - x)
            y += t ** (control_points + 1) * (end_y - y)
            
            points.append((x, y))
        
        return points
    
    def click_element(self, element, right_click=False):
        """
        Click an element with human-like behavior.
        
        Args:
            element: The element to click
            right_click: Whether to perform a right-click
        """
        try:
            # First move to the element
            self.move_mouse_to_element(element)
            
            # Small pause before clicking
            self.random_sleep(0.1, 0.3)
            
            # Perform the click
            actions = ActionChains(self.browser)
            
            if right_click:
                actions.context_click(element)
            else:
                actions.click(element)
                
            actions.perform()
            
            # Small pause after clicking
            self.random_sleep(0.2, 0.5)
            
        except WebDriverException as e:
            logger.debug(f"Error clicking element: {e}")
    
    def scroll_page(self, direction="down", distance=None, speed="medium"):
        """
        Scroll the page with human-like behavior.
        
        Args:
            direction: "up", "down", "left", or "right"
            distance: Scroll distance in pixels (None for random)
            speed: "slow", "medium", or "fast"
        """
        try:
            # Determine scroll distance
            if distance is None:
                if direction in ["up", "down"]:
                    distance = random.randint(100, 800)
                else:  # left or right
                    distance = random.randint(50, 400)
            
            # Adjust distance for direction
            if direction in ["up", "left"]:
                distance = -distance
            
            # Determine scroll speed (pixels per step)
            speed_map = {
                "slow": (5, 15, 0.01, 0.03),
                "medium": (10, 30, 0.005, 0.02),
                "fast": (20, 60, 0.001, 0.01)
            }
            
            pixels_per_step, max_pixels_per_step, min_delay, max_delay = speed_map.get(
                speed, speed_map["medium"]
            )
            
            # Calculate number of steps
            steps = abs(distance) // pixels_per_step
            if steps == 0:
                steps = 1
            
            # Scroll in steps
            remaining = abs(distance)
            for _ in range(steps):
                # Randomize the amount to scroll in this step
                step_size = min(
                    random.randint(pixels_per_step, max_pixels_per_step),
                    remaining
                )
                
                # Adjust for direction
                if distance < 0:
                    step_size = -step_size
                
                # Perform the scroll
                if direction in ["up", "down"]:
                    self.browser.execute_script(f"window.scrollBy(0, {step_size});")
                else:  # left or right
                    self.browser.execute_script(f"window.scrollBy({step_size}, 0);")
                
                # Random delay between steps
                time.sleep(random.uniform(min_delay, max_delay))
                
                remaining -= abs(step_size)
                if remaining <= 0:
                    break
            
            # Pause after scrolling
            self.random_sleep(0.2, 0.7)
            
        except WebDriverException as e:
            logger.debug(f"Error scrolling page: {e}")
    
    def scroll_to_element(self, element, offset=100):
        """
        Scroll to bring an element into view with human-like behavior.
        
        Args:
            element: The element to scroll to
            offset: Vertical offset from the element (pixels)
        """
        try:
            # Get element position
            element_y = element.location['y']
            
            # Get current scroll position
            current_scroll = self.browser.execute_script("return window.pageYOffset")
            
            # Calculate target scroll position with offset
            target_scroll = element_y - offset
            
            # Calculate distance to scroll
            distance = target_scroll - current_scroll
            
            # Determine direction
            direction = "down" if distance > 0 else "up"
            
            # Scroll with human-like behavior
            self.scroll_page(direction=direction, distance=abs(distance))
            
        except WebDriverException as e:
            logger.debug(f"Error scrolling to element: {e}")
            # Fallback to JavaScript scrolling
            self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    
    def type_text(self, element, text, typing_speed="medium"):
        """
        Type text into an element with human-like typing behavior.
        
        Args:
            element: The element to type into
            text: The text to type
            typing_speed: "slow", "medium", or "fast"
        """
        try:
            # Click the element first
            self.click_element(element)
            
            # Clear the field
            element.clear()
            
            # Determine typing speed (seconds per character)
            speed_map = {
                "slow": (0.1, 0.3),
                "medium": (0.05, 0.15),
                "fast": (0.01, 0.08)
            }
            
            min_delay, max_delay = speed_map.get(typing_speed, speed_map["medium"])
            
            # Type each character with random delay
            for char in text:
                element.send_keys(char)
                
                # Random delay between keystrokes
                time.sleep(random.uniform(min_delay, max_delay))
                
                # Occasionally add a longer pause (simulating thinking)
                if random.random() < 0.05:  # 5% chance
                    time.sleep(random.uniform(0.5, 1.5))
            
            # Pause after typing
            self.random_sleep(0.3, 0.8)
            
        except WebDriverException as e:
            logger.debug(f"Error typing text: {e}")
    
    def random_activity(self, duration=5):
        """
        Perform random browsing activity for a specified duration.
        
        Args:
            duration: Duration in seconds
        """
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Choose a random action
            action = random.choice([
                "scroll", "scroll", "scroll",  # Weight scrolling higher
                "move", "pause"
            ])
            
            try:
                if action == "scroll":
                    direction = random.choice(["up", "down"])
                    self.scroll_page(direction=direction)
                    
                elif action == "move":
                    # Move to a random element on the page
                    elements = self.browser.find_elements(By.TAG_NAME, random.choice(["a", "button", "div", "img"]))
                    if elements:
                        element = random.choice(elements)
                        self.move_mouse_to_element(element)
                        
                elif action == "pause":
                    # Just pause for a moment
                    self.random_sleep(0.5, 2.0)
                    
            except WebDriverException as e:
                logger.debug(f"Error during random activity: {e}")
                self.random_sleep(0.5, 1.0)
                
        logger.debug(f"Completed random activity for {duration} seconds")

# Standalone functions for simpler use cases

def random_scroll(browser, direction="down", distance=None):
    """
    Perform a random scroll on the page.
    
    Args:
        browser: The browser instance
        direction: "up", "down", "left", or "right"
        distance: Scroll distance in pixels (None for random)
    """
    simulator = HumanBehaviorSimulator(browser)
    simulator.scroll_page(direction=direction, distance=distance)

def human_click(browser, element):
    """
    Click an element with human-like behavior.
    
    Args:
        browser: The browser instance
        element: The element to click
    """
    simulator = HumanBehaviorSimulator(browser)
    simulator.click_element(element)

def human_type(browser, element, text):
    """
    Type text with human-like behavior.
    
    Args:
        browser: The browser instance
        element: The element to type into
        text: The text to type
    """
    simulator = HumanBehaviorSimulator(browser)
    simulator.type_text(element, text) 