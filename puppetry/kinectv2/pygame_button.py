#!/usr/bin/env python3
"""\
@file pygame_button.py

@brief Simple button class so this can have basic UI

$LicenseInfo:firstyear=2022&license=viewerlgpl$
Second Life Viewer Source Code
Copyright (C) 2022, Linden Research, Inc.
 
This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation;
version 2.1 of the License only.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Linden Research, Inc., 945 Battery Street, San Francisco, CA  94111  USA
$/LicenseInfo$
"""



import pygame

LEFT_CLICK = 0

BTN_TEXT_SIZE = 28
BTN_COLOR = (64,64,64)
BTN_HOVER_COLOR = (1,160,160)
BTN_TEXT_COLOR = (255,255,255)

#Pygame Colors
# pgBlack,pgWhite,pgDarkGrey,pgLightGrey = (0,0,0),(255,255,255),(150,150,150),(211,211,211)
# pgRed,pgDarkRed,pgLightRed,pgReallyLightRed = (255,0,0),(150,0,0),(255,100,100),(255,200,200)
# pgGreen,pgDarkGreen,pgLightGreen,pgReallyLightGreen = (0,255,0),(0,150,0),(100,255,100),(200,255,200)
# pgBlue,pgDarkBlue,pgLightBlue,pgReallyLightBlue = (0,0,255),(0,0,150),(100,100,255),(200,200,255)
# pgYellow,pgDarkYellow,pgGold = (255,255,0),(200,200,0),(212,175,55)


#Display images
# def imageDisplay(Image_name,Width,Height,x,y):
#     Image = pygame.image.load(f"{Image_name}")
#     Image = pygame.transform.scale(Image,(Width,Height))
#     ImageRect = Image.get_rect()
#     ImageRect.center = (x,y)
#     Window.blit(Image,ImageRect)
#     return ImageRect.center,Image

# For logging, set log_function to a function that expects a string
import puppetry

PYGLogger = puppetry.log

def log_msg(message):
    """ Send out string to a log """
    if PYGLogger is not None:
        PYGLogger(message)




# Simple button class for pygame_x
class PYGButton(object):

    def __init__(self, center_x, center_y, width, height, 
                button_color, hover_color,
                name, text, text_size, text_color, click_callback = None):
        """ make a button """
        self._left = center_x - (width // 2)
        self._top = center_y - (height // 2)
        self._width = width
        self._height = height
        self._right = self._left + width
        self._bottom = self._top + height
        self._color = button_color
        self._hover_color = hover_color
        self._name = name
        self._label = text
        self._text_size = text_size
        self._text_color = text_color
        self._click_callback = click_callback
        self._mouse_down = False

        self._font = pygame.font.Font("freesansbold.ttf", text_size)

        font_size = self._font.size(self._label)
        self._text_x = (center_x - (font_size[0] // 1.5))
        self._text_y = (center_y - (font_size[1] // 2))


    def drawNormal(self, surface):
        """ Draw normal frame, color and text for button """
        pygame.draw.rect(surface, self._color, (self._left, self._top, self._width, self._height))              
        rendered_text = self._font.render(F"{self._label}",True, self._text_color)
        surface.blit(rendered_text, [self._text_x, self._text_y])


    def drawHover(self, surface, mouse_down):
        """ Draw hover frame, color and text for button  TO DO - use mouse_down, add _text_hover_color ?"""
        pygame.draw.rect(surface, self._hover_color, (self._left, self._top, self._width, self._height))              
        rendered_text = self._font.render(F"{self._label}",True, self._text_color)
        shift = 4 if mouse_down else 0  
        surface.blit(rendered_text, [self._text_x + shift, self._text_y + shift])


    def mouseOverButton(self, mouse_pos):
        """ Return True if mouse is over the button space """
        mob = mouse_pos[0] > self._left and mouse_pos[0] < self._right and \
              mouse_pos[1] > self._top and mouse_pos[1] < self._bottom
        # log_msg("MOB %s : (%r,%r) x (%r, %r), mouse %r over: %r" % 
        #                 (self._label, self._left, self._top, self._right, self._bottom,
        #                 mouse_pos, mob))
        return mob

    def handleMouse(self, surface, mouse_pos, mouse_down):
        """ Process the given mouse state once per frame """
        mob = self.mouseOverButton(mouse_pos)
        if mob:
            if self._mouse_down and not mouse_down and \
                self._click_callback is not None:
                # mouse was down, now up -> click
                self._click_callback(self._name)
            self._mouse_down = mouse_down
            self.drawHover(surface, mouse_down)
        else:       # Mouse outside
            self._mouse_down = False
            self.drawNormal(surface)
 

#---------------------------------------------------------------

# One Button manager to rule them all
class PYGButtonManager(object):
    def __init__(self, surface):
        """ constructor """
        self._surface = surface
        self._buttons = {}

    def createButton(self, name, label,
                    center_x, center_y, width, height,
                    click_callback,
                    text_size = BTN_TEXT_SIZE,
                    text_color = BTN_TEXT_COLOR,
                    button_color = BTN_COLOR, 
                    hover_color = BTN_HOVER_COLOR):
        """ Create a new button"""
        if name not in self._buttons:
            self._buttons[name] = PYGButton(center_x, center_y, width, height, 
                                    button_color, hover_color,
                                    name, label, text_size, text_color, click_callback)
        else:
            raise Exception("Can't create same button %r twice" % name)

    def idle(self, mouse_pos):
        """ Called once per frame to handle events and draw.
            Mouse postions are scaled to the full image (not screen) size """
        mouse_down = pygame.mouse.get_pressed()[LEFT_CLICK]
        for _, cur_button in self._buttons.items():
            cur_button.handleMouse(self._surface, mouse_pos, mouse_down)
