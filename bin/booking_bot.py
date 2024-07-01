import argparse
import time
from datetime import datetime, timezone

import pytz

from hsp.course import Course
from hsp.errors import CourseNotBookable
from hsp.booking import HSPCourse, start_chrome, start_edge
from hsp.main import parse_credentials

courses = [
    # TEST
    Course("12231858", "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Floorball_Spielbetrieb.html"),
    # Course("13531235", "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Flag-Football_Level_2.html"),
    # Course("15131246", "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Softball_Level_2_-_3.html", password="password"),

    # REAL: SS 2024/2
    # Course("21232116", "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Trampolin_Treff_Level_1.html"),
    # Course("21132173", "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Turnen_Level_1.html"),
]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Hochschulsport course booking",
        prog="hsp")
    parser.add_argument('--fire', action='store_true')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()

    fire = args.fire or False
    test = args.test or False
    credentials = parse_credentials("credentials.yaml")
    if not fire:
        tz = pytz.timezone('Europe/Berlin')
        cest_now = datetime.now(tz)
        booking_start = cest_now.replace(hour=15, minute=59, second=45, microsecond=0)
        booking_cutoff = cest_now.replace(hour=16, minute=2, second=45, microsecond=0)
        print(f"booking window: {booking_start} - {booking_cutoff}")
        while datetime.now(tz) < booking_start:
            print(f"waiting {datetime.now(tz)}")
            time.sleep(1)
        print("ready")

    driver = start_edge()
    for course in courses:
        print(f"[*] Booking course {course.id}")
        try:
            booked = False
            info_printed = False
            while not booked:
                try:
                    booking = HSPCourse(course, driver)
                    if not info_printed:
                        print("... " + booking.info())
                        info_printed = True
                    booking.book(credentials, test)
                    booked = True
                except CourseNotBookable:
                    if fire:
                        raise
                    if datetime.now(tz) < booking_cutoff:
                        print(f"unable to book yet {datetime.now(tz)}")
                        time.sleep(1)
                    else:
                        print(f"past booking cutoff, not retrying")
                        raise
        except Exception as e:
            print(f"[ERROR] Failed to book course {course.id}")
    pass
