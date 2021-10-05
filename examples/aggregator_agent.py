import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO)


# def check_for_devices():
#     pass


# def check_for_data():
#     pass


class AggregatorAgent:
    def __init__(self) -> None:
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(
            self.__class__.check_for_devices,
            args=[self],
            trigger="interval",
            seconds=10,
        )
        self.scheduler.add_job(
            self.__class__.check_for_data,
            args=[self],
            trigger="interval",
            seconds=3,
        )

    def start(self):
        print(
            "Press Ctrl+{0} to exit".format(
                "Break" if os.name == "nt" else "C"
            )
        )
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass

    def check_for_devices(self):
        logging.info(">>>>>>>>>>>>>> checking for devices")
        raise NotImplementedError

    def check_for_data(self):
        logging.info(">>>>>>>>>>>>> checking for data")
        raise NotImplementedError


class JetChargeAgent(AggregatorAgent):
    def check_for_devices(self):
        logging.info("************** checking for devices")

    def check_for_data(self):
        logging.info("************** checking for data")


def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(check_for_devices, "interval", seconds=10)
    scheduler.add_job(check_for_data, "interval", seconds=3)
    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    client = JetChargeClient()
    client.start()
