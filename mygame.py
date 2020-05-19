import itertools
import math

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3
from panda3d.core import WindowProperties


class HackableApp(ShowBase):
    def __init__(self, width=None, height=None):
        super().__init__(self)

        self.disableMouse()
        if width is not None and height is not None:
            self.resize_window(width, height)
        elif width is not None or height is not None:
            raise ValueError("must specify both of height/width or neither")

        self.renderables = []

    def resize_window(self, width, height):
        window_prop = WindowProperties()
        window_prop.setSize(width, height)
        self.win.requestProperties(window_prop)

    def add_renderable(self, renderable):
        self.renderables.append(renderable)
        renderable.reparentTo(self.render)

    def add_task(self, func, continuous=True):
        if continuous:
            def wrapped_func(task):
                func(self, task)
                return Task.cont
        else:
            def wrapped_func(task):
                func(self, task)
        self.taskMgr.add(wrapped_func, func.__name__)


def _loopable_value(list_or_val, default_val=1):
    if list_or_val is None:
        return [default_val]
    try:
        iter(list_or_val)
        return list_or_val
    except TypeError:
        return [list_or_val]


def invoke_interval_point3_loop(bound_actor_method, points, durations=None):
    durations = _loopable_value(durations)
    loop = Sequence(
        *[
            bound_actor_method(dur, Point3(pt), Point3(prv))
            for prv, pt, dur in zip(
                points,
                points[1:] + [points[0]],
                itertools.cycle(durations),
            )
        ],
        # name=f"{actor!r} loop: pts{points}",
    )
    loop.loop()
    # todo :: I think this will likely get GC'd, figure that out.


def actor_add_pos_loop(actor, points, durations=None):
    invoke_interval_point3_loop(actor.posInterval, points, durations)


def actor_add_heading_loop(actor, points, durations=None):
    invoke_interval_point3_loop(actor.hprInterval, points, durations)


RADS_TO_DEGS = 180 / math.pi


def get_smoothed_hprs(headings):
    # smooths headings but you still get a jump start to end
    # such terrible code
    # hard to avoid having a big spin at the end with finite loops;
    # probably need to add a 0-time interval
    # but I can't be bothered implementing atm
    # so works nicely iff the final angle is 180deg turn or something
    def get_closer(heading, prev):
        min, argmin = 999999, 0
        for i in range(-10, 10):
            if (new := abs((angle := heading + 360 * i) - prev)) < min:
                min = new
                argmin = angle
        return argmin
    new_headings = [headings[0]]
    for next in headings[1:]:
        new_headings.append(get_closer(next, new_headings[-1]))
    return [Point3(heading, 0, 0) for heading in new_headings]


def actor_path_with_turn_anim(actor, points, durations=None, turn_anim_time=0.2):
    durations = _loopable_value(durations)
    actor_add_pos_loop(actor, points, durations)
    actor_add_heading_loop(
        actor,
        get_smoothed_hprs(
            [
                -90 + math.atan2(vec.y, vec.x) * RADS_TO_DEGS
                for a, b in zip(points, points[1:] + [points[0]])
                for vec in [Point3(a) - Point3(b)] * 2
            ]
        ),
        [
            x
            for d in durations
            for x in [d * (1 - turn_anim_time), d * turn_anim_time]
        ]
    )


def build_game():
    game = HackableApp(1280, 720)

    # add some trees n stuff
    scene = loader.loadModel("models/environment")
    scene.setScale(*[0.1] * 3)
    scene.setPos(-5, 40, 0)
    game.add_renderable(scene)

    panda = Actor("models/panda-model", {"walk": "models/panda-walk4"})
    panda.setScale(*[0.003] * 3)
    panda.loop("walk")
    game.add_renderable(panda)

    actor_path_with_turn_anim(
        panda, [(0, -1, 0), (-2, 0, 0), (0, 1, 0), (3, 0, 0), (2, 1, 0), (2, -1, 0)], 
    )

    # animate camera
    game.add_task(
        lambda app, t: app.camera.setPos(0, - 5 - t.time, 1 + 0.1 * t.time)
    )

    return game


if __name__ == "__main__":
    build_game().run()
