import itertools

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence

from panda3d.core import Point3
from panda3d.core import WindowProperties
from panda3d.core import AmbientLight, PointLight, DirectionalLight
from panda3d.core import Vec2, Vec4


def get_ambient_light(r, g, b):
    light = AmbientLight(f"ambientlight {r} {g} {b}")
    light.setColor(Vec4(r, g, b, 1))
    return light


def get_point_light(r, g, b, const=1, linear=0, quadratic=1, shadows=True):
    light = PointLight(f"pointlight {r} {g} {b}")
    light.setColor(Vec4(r, g, b, 1))
    light.setAttenuation((const, linear, quadratic))  # c l q
    if shadows:
        light.setShadowCaster(True)
    return light


def get_directional_light(r, g, b, shadows=True):
    light = DirectionalLight(f"directionallight {r} {g} {b}")
    light.setColor(Vec4(r, g, b, 1))
    if shadows:
        light.setShadowCaster(True)  # doesn't seem to work?
        # todo :: need to figure out how lenses work at some point
    return light


class HackableApp(ShowBase):
    def __init__(self, width=None, height=None):
        super().__init__(self)

        self.disableMouse()
        if width is not None and height is not None:
            self.resize_window(width, height)
        elif width is not None or height is not None:
            raise ValueError("must specify both of height/width or neither")

        self.render.setShaderAuto()

        self.object_list = []

    def resize_window(self, width, height):
        window_prop = WindowProperties()
        window_prop.setSize(width, height)
        self.win.requestProperties(window_prop)

    def add_object(self, obj, to_render=False, scale=None, pos=None):
        if scale is not None:
            obj.setScale(scale)
        if pos is not None:
            obj.setPos(*pos)
        self.object_list.append(obj)
        obj.reparentTo(self.render)

    def add_renderable(self, renderable, scale=None, pos=None):
        self.add_object(renderable, to_render=True, scale=scale, pos=pos)

    def add_render_node(self, node):
        nodepath = self.render.attachNewNode(node)
        self.object_list.append(nodepath)
        return nodepath

    def add_light(self, light, pos=None, hpr=None):
        nodepath = self.add_render_node(light)
        if pos is not None:
            nodepath.setPos(*pos)
        if hpr is not None:
            nodepath.setHpr(*hpr)
        self.render.setLight(nodepath)  # just added

    def add_ambient_light(self, r, g, b):
        self.add_light(get_ambient_light(r, g, b))

    def add_point_light(self, r, g, b, pos=None):
        self.add_light(get_point_light(r, g, b), pos=pos)

    def add_directional_light(self, r, g, b, hpr=None):
        self.add_light(get_directional_light(r, g, b), hpr=hpr)

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
                points, points[1:] + [points[0]], itertools.cycle(durations),
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


def actor_path_with_turn_anim(
    actor, points, durations=None, turn_anim_time=0.2
):
    durations = _loopable_value(durations)
    actor_add_pos_loop(actor, points, durations)
    actor_add_heading_loop(
        actor,
        get_smoothed_hprs(
            [
                Vec2(0, 1).signedAngleDeg(vec.getXy())
                for a, b in zip(points, points[1:] + [points[0]])
                for vec in [Point3(a) - Point3(b)] * 2
            ]
        ),
        [
            x
            for d in durations
            for x in [d * (1 - turn_anim_time), d * turn_anim_time]
        ],
    )


def load_and_animate(
    model, animations, follow_path=None, **follow_path_kwargs,
):
    actor = Actor(model, animations)
    actor.loop(list(animations)[0])
    if follow_path is not None:
        actor_path_with_turn_anim(actor, follow_path, **follow_path_kwargs)
    return actor


def build_game():
    game = HackableApp(1280, 720)

    # add some trees n stuff
    game.add_renderable(
        loader.loadModel("models/environment"), scale=0.1, pos=(-5, 40, 0),
    )

    game.add_renderable(
        load_and_animate(
            "models/panda-model",
            {"walk": "models/panda-walk4"},
            follow_path=[
                (0, -1, 0),
                (-2, 0, 0),
                (0, 1, 0),
                (3, 0, 0),
                (2, 1, 0),
                (2, -1, 0),
            ],
        ),
        scale=0.003,
    )

    # animate camera
    game.add_task(
        lambda app, t: app.camera.setPos(0, -5 - t.time, 1 + 0.1 * t.time)
    )

    # add lighting
    game.add_ambient_light(0.3, 0.1, 0.1)
    game.add_point_light(0.1, 0.3, 0.6, pos=(0, 0, 2))
    game.add_directional_light(0.3, 0.3, 0.3, hpr=(30, -45, 0))
    game.add_directional_light(0, 0.3, 0.1, hpr=(60, -60, 0))
    game.add_directional_light(0, 0.1, 0.4, hpr=(-5, -60, 0))

    return game


if __name__ == "__main__":
    build_game().run()
