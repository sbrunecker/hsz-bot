# HSZ Booking Bot

# Setup

- Install Python 3.12 or newer
- Create a virtual environment: `python -m venv venv`
- Activate the virtual environment: 
  - Linux: `source venv/bin/activate`
  - Windows: `venv\Scripts\activate.ps1`
- Install dependencies: `pip install .`

## Booking

- Adjust the bot for your browser in `booking_bot.py`
  - Replace `driver = start_edge()` with `driver = start_chrome()` or `driver = start_firefox()`
  - WARNING: Not tested with Firefox
- Adjust `credentials.yaml`
  - status: `S-RWTH` -> student
  - pid: matriculation number
  - password: Delete the password line if you don't have one
- Find the URLs and course IDs of the courses you want to book and enter them in booking_bot.py
- Run the script `python bin/booking_bot.py`

### Test Run

- Use one of the existing courses in the TEST section in `booking_bot.py`, comment the other ones
- Run the script `python bin/booking_bot.py --fire --test`