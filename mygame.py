import itertools
import math

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence
from panda3d.core import Point3


class HackableApp(ShowBase):
    def __init__(self):
        super().__init__(self)
        self.renderables = []

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


def invoke_interval_point3_loop(bound_actor_method, points, durations=None):
    if durations is None:
        durations = 1
    try:
        iter(durations)
    except TypeError:
        durations = [durations]
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


def actor_path_with_turn_anim(actor, points, durations=[1], turn_anim_time=0.2):
    actor_add_pos_loop(actor, points, durations)
    actor_add_heading_loop(
        actor,
        [
            Point3(math.atan2(vec.x, vec.y) * RADS_TO_DEGS, 0, 0)
            for a, b in zip(points, points[1:] + [points[0]])
            for vec in [(Point3(a) - Point3(b))] * 2
        ],
        [
            x
            for d in durations
            for x in [d * (1 - turn_anim_time), d * turn_anim_time]
        ]
    )


def build_game():
    game = HackableApp()

    # add some trees n stuff
    scene = game.loader.loadModel("models/environment")
    scene.setScale(*[0.1] * 3)
    scene.setPos(-5, 40, 0)
    game.add_renderable(scene)

    panda = Actor("models/panda-model", {"walk": "models/panda-walk4"})
    panda.setScale(*[0.003] * 3)
    panda.loop("walk")
    game.add_renderable(panda)

    actor_path_with_turn_anim(panda, [(0, -1, 0), (0, 1, 0)], [3, 3])

    # animate camera
    game.add_task(
        lambda app, t: app.camera.setPos(0, -t.time, 0.1 * t.time)
    )

    return game


if __name__ == "__main__":
    build_game().run()
