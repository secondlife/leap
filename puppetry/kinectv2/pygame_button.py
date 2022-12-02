"""
pygame_button.py

This is a simple button class running under pygame, attempting to be
independant of the application and usable in other programs

"""
import pygame

LEFT_CLICK = 0

BTN_TEXT_SIZE = 28
BTN_COLOR = (64,64,64)
BTN_HOVER_COLOR = (1,160,160)
BTN_TEXT_COLOR = (255,255,255)

def default_logger(message):
    """ Default to normal print() for log messages """
    print(message)

class PYGLogger():
    """ log message routing """
    def __init__(self):
        """ just use default """
        self.set_logger(default_logger)

    def set_logger(self, logger_func):
        """ Set alternative function """
        self._logger_func = default_logger

    def msg(self, log_msg):
        """ Route the message to log function """
        self._logger_func(log_msg)

button_logger = PYGLogger()



#---------------------------------------------------------------

class PYGButton():
    """ Simple button class for pygame_x """
    def __init__(self, button_info, click_callback = None):
        """ make a button """

        self._width = button_info['width']
        self._height = button_info['height']
        self._left = button_info['center_x'] - (self._width // 2)
        self._top = button_info['center_y'] - (self._height // 2)
        self._right = self._left + self._width
        self._bottom = self._top + self._height
        self._color = button_info['button_color']
        self._hover_color = button_info['hover_color']
        self._name = button_info['name']
        self._label = button_info['label']
        self._text_size = button_info['text_size']
        self._text_color = button_info['text_color']
        self._click_callback = click_callback
        self._mouse_down = False

        self._font = pygame.font.Font("freesansbold.ttf", button_info['text_size'])

        font_size = self._font.size(self._label)
        self._text_x = (button_info['center_x'] - (font_size[0] // 1.5))
        self._text_y = (button_info['center_y'] - (font_size[1] // 2))
        button_logger.msg(f'Created button {self._name}')


    def draw_normal(self, surface):
        """ Draw normal frame, color and text for button """
        pygame.draw.rect(surface, self._color, (self._left, self._top, self._width, self._height))
        rendered_text = self._font.render(F"{self._label}",True, self._text_color)
        surface.blit(rendered_text, [self._text_x, self._text_y])


    def draw_hover(self, surface, mouse_down):
        """ Draw hover frame, color and text for button  TO DO - use mouse_down, add _text_hover_color ?"""
        pygame.draw.rect(surface, self._hover_color, (self._left, self._top, self._width, self._height))
        rendered_text = self._font.render(F"{self._label}",True, self._text_color)
        shift = 4 if mouse_down else 0
        surface.blit(rendered_text, [self._text_x + shift, self._text_y + shift])


    def mouse_over_button(self, mouse_pos):
        """ Return True if mouse is over the button space """
        mob = mouse_pos[0] > self._left and mouse_pos[0] < self._right and \
              mouse_pos[1] > self._top and mouse_pos[1] < self._bottom
        # button_logger.msg(f'MOB self._label : '
        #           f'({self._left},{self._top}) x ({self._right}, {self._bottom}), '
        #           f'mouse {mouse_pos} over: {mob}'
        return mob

    def handle_mouse(self, surface, mouse_pos, mouse_down):
        """ Process the given mouse state once per frame
            deal with hovering and clicks """
        mob = self.mouse_over_button(mouse_pos)
        if mob:
            if self._mouse_down and not mouse_down and \
                self._click_callback is not None:
                # mouse was down, now up -> click
                self._click_callback(self._name)
            self._mouse_down = mouse_down
            self.draw_hover(surface, mouse_down)
        else:       # Mouse outside
            self._mouse_down = False
            self.draw_normal(surface)


#---------------------------------------------------------------

class PYGButtonManager():
    """ One Button manager to rule them all
        To do:
            delete_button(self, name)
    """
    def __init__(self, surface):
        self._surface = surface
        self._buttons = {}

    def create_button(self, new_info, click_callback = None):
        """ Create a new button"""

        name = new_info['name']
        if name not in self._buttons:
            button_info = {'name' : name,
                        'text_size' : BTN_TEXT_SIZE,
                        'text_color' : BTN_TEXT_COLOR,
                        'button_color' : BTN_COLOR,
                        'hover_color' : BTN_HOVER_COLOR}

            if 'text_size' in new_info:
                button_info['text_size'] = new_info['text_size']
            if 'text_color' in new_info:
                button_info['text_color'] = new_info['text_color']
            if 'button_color' in new_info:
                button_info['button_color'] = new_info['button_color']
            if 'hover_color' in new_info:
                button_info['hover_color'] = new_info['hover_color']

            button_info['label'] = new_info['label']
            button_info['center_x'] = new_info['center_x']
            button_info['center_y'] = new_info['center_y']
            button_info['width'] = new_info['width']
            button_info['height'] = new_info['height']

            self._buttons[name] = PYGButton(button_info, click_callback)
        else:
            raise Exception(f"Can't create same button {name} twice")

    def delete_button(self, name):
        """ Remove a button """
        if name in self._buttons:
            del self._buttons[name]

    def idle(self, mouse_pos):
        """ Called once per frame to handle events and draw.
            Mouse postions are scaled to the full image (not screen) size """
        mouse_down = pygame.mouse.get_pressed()[LEFT_CLICK]
        for _, cur_button in self._buttons.items():
            cur_button.handle_mouse(self._surface, mouse_pos, mouse_down)
