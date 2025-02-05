from .credentials import Credentials
from .cli import parse_args
from .booking import (HSPCourse, start_firefox, start_headless_firefox,
                      start_chrome, start_headless_chrome)
from .errors import (InvalidCredentials, CourseNotBookable, CourseIdNotListed)


def parse_credentials(credfile):
    if credfile.upper().endswith(".JSON"):
        credentials = Credentials.from_json(credfile)
    else:  # its a yaml file
        credentials = Credentials.from_yaml(credfile)
    return credentials


def main():

    args = parse_args()

    if args.subcommand == "check-credentials":
        print("[*] HSP Credential-File Checking")
        try:
            credentials = parse_credentials(args.credentials)
        except InvalidCredentials as e:
            print(e)
            print("[!] INVALID CREDENTIALS")
        else:
            print("Credentials are most likely O.K. :)")

    else:
        if args.use_firefox:
            driver = start_firefox()
        elif args.use_headless_firefox:
            driver = start_headless_firefox()
        elif args.use_chrome:
            driver = start_chrome()
        else:
            driver = start_headless_chrome()

        try:
            course = HSPCourse("12232856", "https://buchung.hsz.rwth-aachen.de/angebote/Wintersemester_2022_23/_Floorball_Spielbetrieb.html", driver)
        except CourseIdNotListed:
            print("[ERROR] Course ID not listed")
            exit(1)

        if args.subcommand == "course-status":
                print("[*] HSP Course Status")
                print("... " + course.info())
                print("... " + course.status())

        elif args.subcommand == "booking":
            print("[*] HSP Course Booking")
            credentials = parse_credentials(args.credentials)
            print("... " + course.info())
            try: course.book(credentials)
            except CourseNotBookable:
                print("... " + course.status())
                print("[ERROR] Course cannot be booked")


if __name__ == "__main__":
    main()
