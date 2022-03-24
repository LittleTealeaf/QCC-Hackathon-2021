import requests
import time
import schedule
from plyer import notification

weather_key = 'ced1e7c15afb4b33a63140847211004'
location_key = 'f23e1e65311b9be7d2ccc2dc3e2a1f1e'


def get_steps():
    loc = requests.get("http://api.ipstack.com/check", params={
        'access_key': location_key
    }).json()

    raw_json = requests.get("https://api.weatherapi.com/v1/forecast.json", params={
        'key': weather_key,
        'q': loc['zip'],
        'days': 2
    }).json()
    today = raw_json['forecast']['forecastday'][0]['hour']
    tomorrow = raw_json['forecast']['forecastday'][1]['hour']

    # Get day and night
    day = list()
    night = list()
    end = False
    for h in range(24):
        if today[h]['is_day'] == 1:
            day.append(today[h])
        elif len(day) > 0:
            night.append(today[h])
        if tomorrow[h]['is_day'] == 1:
            end = True
        if not end and tomorrow[h]['is_day'] == 0:
            night.append(tomorrow[h])
    evaluate_night(night)
    evaluate_day(day)
    steps = get_json_steps(day + night)

    return steps


def evaluate_night(night):
    # Get the night's start tim
    temps = list()
    humidity = list()
    wind = list()
    rain = list()
    for h in range(len(night)):
        temps.append(night[h]['temp_f'])
        humidity.append(night[h]['humidity'])
        wind.append(night[h]['wind_mph'])
        rain.append(night[h]['will_it_rain'])
    average_humidity = sum(humidity) / float(len(humidity))
    average_temp = sum(temps) / float(len(temps))
    windows = average_humidity < 40 and 60 < average_temp < 75 and sum(rain) == 0
    ac = average_temp > 85
    heat = average_temp < 50

    for h in range(len(night)):
        night[h]['windows'] = windows
        night[h]['ac'] = not windows and ac
        night[h]['heat'] = not windows and heat


def evaluate_day(day):
    for h in range(len(day)):
        day[h]['windows'] = day[h]['humidity'] < 60 and 68 < day[h]['temp_f'] < 74 and not day[h]['will_it_rain'] == 1
        day[h]['heat'] = not day[h]['windows'] and day[h]['temp_f'] < 67
        day[h]['ac'] = not day[h]['windows'] and day[h]['temp_f'] > 80


def get_json_steps(hours):
    # Sort Hours
    def get_hour(hour):
        return hour['time_epoch']

    def format_time(timestamp):
        return timestamp[len(timestamp) - 5:]

    def indicate_change(previous, current):
        ret = ""
        if previous['windows'] != current['windows']:
            if previous['windows']:
                ret += "close windows, "
            else:
                ret += "open windows, "
        if previous['heat'] != current['heat']:
            if previous['heat']:
                ret += "turn off heat, "
            else:
                ret += 'turn on heat, '
        if previous['ac'] != current['ac']:
            if previous['ac']:
                ret += "turn off ac, "
            else:
                ret += "turn on ac, "
        if len(ret) > 0:
            return ret[:len(ret) - 2]
        else:
            return None

    hours.sort(key=get_hour)
    instructions = list()

    for h in range(1, len(hours)):
        steps = indicate_change(hours[h-1], hours[h])
        if steps is not None:
            instructions.append({'time': format_time(hours[h]['time']), 'instruction': steps})
    return instructions


def setup_notifications(steps):
    def execute_notification(step):
        notification.notify(
            title="Climate Control Step",
            message=step['instruction'],
            timeout=50
        )
        return schedule.CancelJob

    for i in range(len(steps)):
        schedule.every().day.at(str(steps[i]['time'])).do(execute_notification, steps[i])


def daily_execute():
    steps = get_steps()
    for i in range(len(steps)):
        print(steps[i]['time'] + " " + steps[i]['instruction'])

    schedule.clear()
    setup_notifications(steps)
    schedule.every().day.at("00:05").do(daily_execute)
    return schedule.CancelJob


if __name__ == '__main__':
    daily_execute()
    print("Starting")
    while True:
        schedule.run_pending()
        time.sleep(60)
