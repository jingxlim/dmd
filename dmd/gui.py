
class DraggableRectangle:
    """
    Original class by Jorge Scandaliaris with modifications by Davis Bennett. Copied from
    https://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg14543.html

    Draggable and resizeable rectangle with the animation blit techniques.
    Based on example code at
    http://matplotlib.sourceforge.net/users/event_handling.html
    If *allow_resize* is *True* the recatngle can be resized by dragging its
    lines. *border_tol* specifies how close the pointer has to be to a line for
    the drag to be considered a resize operation. Dragging is still possible by
    clicking the interior of the rectangle. *fixed_aspect_ratio* determines if
    the rectangle keeps its aspect ratio during resize operations.
    """
    lock = None  # only one can be animated at a time

    def __init__(self, rect, border_tol=.15, allow_resize=True,
                 fixed_aspect_ratio=False):
        self.rect = rect
        self.border_tol = border_tol
        self.allow_resize = allow_resize
        self.fixed_aspect_ratio = fixed_aspect_ratio
        self.press = None
        self.background = None
        self.cidpress = None
        self.cidrelease = None
        self.cifmotion = None
        self.dx = None
        self.dy = None

    def connect(self):
        """connect to all the events we need"""
        self.cidpress = self.rect.figure.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.rect.figure.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = self.rect.figure.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)

    def on_press(self, event):
        """on button press we will see if the mouse is over us and store some data"""

        from numpy import true_divide
        if event.inaxes != self.rect.axes:
            return
        if DraggableRectangle.lock is not None:
            return
        contains, attrd = self.rect.contains(event)
        if not contains:
            return

        x0, y0 = self.rect.xy
        w0, h0 = self.rect.get_width(), self.rect.get_height()
        aspect_ratio = true_divide(w0, h0)
        self.press = x0, y0, w0, h0, aspect_ratio, event.xdata, event.ydata
        DraggableRectangle.lock = self

        # draw everything but the selected rectangle and store the pixel buffer
        canvas = self.rect.figure.canvas
        axes = self.rect.axes
        self.rect.set_animated(True)
        canvas.draw()
        self.background = canvas.copy_from_bbox(self.rect.axes.bbox)

        # now redraw just the rectangle
        axes.draw_artist(self.rect)

        # and blit just the redrawn area
        canvas.blit(axes.bbox)

    def on_motion(self, event):
        """on motion we will move the rect if the mouse is over us"""
        if DraggableRectangle.lock is not self:
            return
        if event.inaxes != self.rect.axes: return
        x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
        self.dx = event.xdata - xpress
        self.dy = event.ydata - ypress

        self.update_rect()

        canvas = self.rect.figure.canvas
        axes = self.rect.axes
        # restore the background region
        canvas.restore_region(self.background)

        # redraw just the current rectangle
        axes.draw_artist(self.rect)

        # blit just the redrawn area
        canvas.blit(axes.bbox)

    def on_release(self, event):
        'on release we reset the press data'
        if DraggableRectangle.lock is not self:
            return

        self.press = None
        DraggableRectangle.lock = None

        # turn off the rect animation property and reset the background
        self.rect.set_animated(False)
        self.background = None

        # redraw the full figure
        self.rect.figure.canvas.draw()

    def disconnect(self):
        'disconnect all the stored connection ids'
        self.rect.figure.canvas.mpl_disconnect(self.cidpress)
        self.rect.figure.canvas.mpl_disconnect(self.cidrelease)
        self.rect.figure.canvas.mpl_disconnect(self.cidmotion)

    def update_rect(self):
        from numpy import true_divide
        x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
        dx, dy = self.dx, self.dy
        bt = self.border_tol
        fixed_ar = self.fixed_aspect_ratio
        if (not self.allow_resize or
            (abs(x0 + true_divide(w0, 2) - xpress) < true_divide(w0, 2) - bt * w0 and
             abs(y0 + true_divide(h0, 2) - ypress) < true_divide(h0, 2) - bt * h0)):
            self.rect.set_x(x0 + dx)
            self.rect.set_y(y0 + dy)
        elif abs(x0 - xpress) < bt * w0:
            self.rect.set_x(x0 + dx)
            self.rect.set_width(w0 - dx)
            if fixed_ar:
                dy = true_divide(dx, aspect_ratio)
                self.rect.set_y(y0 + dy)
                self.rect.set_height(h0 - dy)
        elif abs(x0 + w0 - xpress) < bt * w0:
            self.rect.set_width(w0 + dx)
            if fixed_ar:
                dy = true_divide(dx, aspect_ratio)
                self.rect.set_height(h0 + dy)
        elif abs(y0 - ypress) < bt * h0:
            self.rect.set_y(y0 + dy)
            self.rect.set_height(h0 - dy)
            if fixed_ar:
                dx = dy * aspect_ratio
                self.rect.set_x(x0 + dx)
                self.rect.set_width(w0 - dx)
        elif abs(y0 + h0 - ypress) < bt * h0:
            self.rect.set_height(h0 + dy)
            if fixed_ar:
                dx = dy * aspect_ratio
                self.rect.set_width(w0 + dx)


class ROI(object):
    """class for representing a single polygonal ROI"""
    def __init__(self, image=[], x=[], y=[]):
        if image is not None:
            self.image = image
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y

    def __repr__(self):
        return 'An ROI containing {0} points'.format(len(self.x))

    def reset(self):
        self.x = []
        self.y = []

    def get_mask(self):
        from matplotlib.path import Path
        from numpy import meshgrid, zeros, array, where
        data = self.image
        mask = zeros(data.shape, dtype='uint8')

        if (len(self.y) > 2) & (len(self.x) > 2):

            points = list(zip(self.y, self.x))

            grid = meshgrid(range(data.shape[0]), range(data.shape[1]))
            coords = list(zip(grid[0].ravel(), grid[1].ravel()))

            path = Path(points)
            in_points = array(coords)[where(path.contains_points(coords))[0]]
            in_points = [tuple(x) for x in in_points]
            for t in in_points:
                mask[t] = 255
        else:
            print('Mask requires 3 or more points')

        return mask


class RoiDrawing(object):
    """Class for drawing ROI on matplotlib figures"""
    def __init__(self, ax, image_data):
        self.image_axes = ax
        self._focus_index = -1
        self.image_data = image_data
        self.lines = []
        self.rois = []
        self.cid_press = self.image_axes.figure.canvas.mpl_connect('button_press_event', self.onpress)
        self.cid_release = self.image_axes.figure.canvas.mpl_connect('button_press_event', self.onpress)
        self.masks = []
        self.selector = []

    @property
    def focus_index(self):
        return self._focus_index

    @focus_index.setter
    def focus_index(self, value):

        if value < 0:
            value = 0
        if value > (len(self.rois) - 1):
            self.new_roi()
        self._focus_index = value

    def focus_incr(self, event=None):
        self.focus_index += 1

    def focus_decr(self, event=None):
        self.focus_index -= 1

    def new_roi(self, event=None):
        self.lines.append(self.image_axes.plot([0], [0])[0])
        self.rois.append(ROI(image = self.image_data, x=[], y=[]))
        self.masks.append(None)

    def onpress(self, event):
        from matplotlib.widgets import Lasso

        if event.inaxes != self.image_axes:
            return
        if self.image_axes.figure.canvas.widgetlock.locked():
            return
        self.focus_incr()
        self.selector = Lasso(event.inaxes, (event.xdata, event.ydata), self.update_line_from_verts)
        self.image_axes.figure.canvas.widgetlock(self.selector)

    def update_line_from_verts(self, verts):
        current_line = self.lines[self.focus_index]
        current_roi = self.rois[self.focus_index]

        for x,y in verts:
            current_roi.x.append(x)
            current_roi.y.append(y)
        self.image_axes.figure.canvas.widgetlock.release(self.selector)
        current_line.set_data(current_roi.x, current_roi.y)
        current_line.figure.canvas.draw()

    def wipe(self, event):
        current_line = self.lines[self.focus_index]
        current_roi = self.rois[self.focus_index]
        current_mask = self.masks[self.focus_index]
        current_roi.reset()
        current_mask = None;
        current_line.set_data(current_roi.x, current_roi.y)
        current_line.figure.canvas.draw()
