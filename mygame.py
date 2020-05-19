from direct.showbase.ShowBase import ShowBase
from direct.task import Task


class Main(ShowBase):
    def __init__(self):
        super().__init__(self)

        scene = self.loader.loadModel("models/environment")
        scene.setScale(*[0.1] * 3)
        scene.setPos(-5, 40, 0)
        self.add_renderable(scene)
        self.add_task(
            lambda app, t: app.camera.setPos(0, -t.time, 0.1 * t.time)
        )

    def add_renderable(self, renderable):
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


if __name__ == "__main__":
    Main().run()
