import datetime, enum, json, os, stat
from collections import Counter, namedtuple

from ui.qt import pywindow, pyelement

STAT_DIR = ".stats"
if not os.path.isdir(STAT_DIR): os.mkdir(STAT_DIR)

class Month(enum.IntEnum):
    January = 1
    February = 2
    March = 3
    April = 4
    May = 5
    June = 6
    July = 7
    August = 8
    September = 9
    October = 10
    November = 11
    December = 12

TrackedResult = namedtuple("TrackedResult", ["data", "month", "year", "read_only"], defaults=[False])

class YearTracker:
    def __init__(self, year, date=None):
        if date is None: date = datetime.date.today()
        self._date = date
        self._year = int(year)

        self._counters = {}
        self._file = os.path.join(STAT_DIR, str(self._year))
        self._dirty = False
        self.load_data()

    def _date_check(self):
        if self.read_only:
            print("WARNING", f"Tried to modify data for an unexpected year {self._year} (current is {self._date.year})")
            return False
        return True

    @property
    def read_only(self): return self._date.year != self._year

    def load_data(self):
        """ (Re)load data from disk """
        try:
            print("VERBOSE", "Loading data for", self._year)
            self._counters.clear()
            with open(self._file, "r") as file:
                data = json.load(file)
                for m in Month:
                    try: self._counters[m.name] = Counter(data[m.name])
                    except KeyError: pass

                totals = data.get("")
                if totals is not None: self._counters[""] = Counter(totals)
        except FileNotFoundError: pass
        self._dirty = False

    def save_data(self, finalize=False):
        """ Save current data to file """
        if self._dirty:

            try:
                print("VERBOSE", "Saving data for", self._year)
                with open(self._file, "w") as file:
                    json.dump(self._counters, file, indent=5)
            except PermissionError:
                print("WARNING", "Tried to save read only data")
                return False
            self._dirty = False

        if finalize:
            print("VERBOSE", f"Marking file {self._file} as read only")
            os.chmod(self._file, stat.S_IREAD|stat.S_IRGRP|stat.S_IROTH)
        return True

    def add(self, item, count=1):
        """
         Adds count for the given item, count must be greater than 0
         If the item doesn't exist yet, the item will be added and set to the given count instead
        """
        if self._date_check():
            try: month = self._counters[Month(self._date.month).name]
            except KeyError: self._counters[Month(self._date.month).name] = month = Counter()
            month[item] += count
            self._dirty = True

    def subtract(self, item, count=-1):
        """
         Subtracts count for the given item, count must be lower than 0
         If the new count is 0 or lower the item is deleted
         Has no effect if the item doesn't exist
        """
        if self._date_check():
            try:
                month = self._counters[Month(self._date.month).name]
                n = month[item] - count
                if n > 0:
                    month[item] = n
                    self._dirty = True
                else: self.remove(item)
            except KeyError: pass

    def _get_month(self, month_filter):
        if isinstance(month_filter, str):
            if month_filter == "current": return Month(self._date.month)
            try: month = Month[month_filter.capitalize()]
            except KeyError: month = None
            if month is None: raise ValueError(f"'{month_filter}' is not a valid Month")
            return month
        elif isinstance(month_filter, int): return Month(month_filter)
        elif isinstance(month_filter, Month): return month_filter
        else: raise TypeError("Unsupported 'month_filter' type")

    def get(self, item, month=None) -> TrackedResult:
        """ Get the count for given item with an optional filter """
        if month is not None and "" not in self._counters:
            month = self._get_month(month)
            try: return TrackedResult(data=self._counters[month.name][item], month=month, year=self._year, read_only=self.read_only)
            except KeyError: return TrackedResult(data=0, month=month, year=self._year, read_only=self.read_only)
        return TrackedResult(data=sum([m[item] for m in self._counters.values()]), month=None, year=self._year, read_only=self.read_only)

    def counter(self, month=None) -> TrackedResult:
        """ Returns a Counter containing all items with an optional filter """
        if month is not None and "" not in self._counters:
            month = self._get_month(month)
            try: return TrackedResult(data=self._counters[month.name].copy(), month=month, year=self._year, read_only=self.read_only)
            except KeyError: return TrackedResult(data=Counter(), month=month, year=self._year, read_only=self.read_only)

        res = Counter()
        for c in self._counters.values(): res += c
        return TrackedResult(data=res, month=None, year=self._year, read_only=self.read_only)

    def remove(self, item):
        """
         Removes the count for this item
         Has no effect if the item doesn't exist
        """
        if self._date_check():
            item = item.lower()
            try: del self._counters[Month(self._date.month).name][item]
            except KeyError: pass
            else: self._dirty = True

    def remove_all(self):
        """ Removes all data from this month """
        try: del self._counters[Month(self._date.month).name]
        except KeyError: pass
        else: self._dirty = True


class SongTracker:
    def __init__(self):
        self._date = datetime.date.today()
        self._trackers = {}
        self._current = self._get_tracker(self._date.year)

    def load_data(self):
        """ (Re)load data from disk """
        for t in self._trackers.values(): t.load_data()

    def save_data(self):
        """ Save current data to file """
        self._current.save_data()

    def _date_check(self):
        new_date = datetime.date.today()
        month_change, year_change = new_date.month != self._date.month, new_date.year != self._date.year
        if month_change or year_change:
            print("VERBOSE", f"Changing month from {Month(self._date.month).name}/{self._date.year} to {Month(new_date.month).name}/{new_date.year}")
            self._date = new_date
            self._current.save_data(finalize=year_change)
            self._current = self._get_tracker(self._date.year)
            for t in self._trackers.values(): t._date = self._date

    @staticmethod
    def _list_years(): return os.listdir(STAT_DIR)

    def _get_tracker(self, year):
        if year == "current": year = self._date.year

        try: return self._trackers[year]
        except KeyError:
            self._trackers[year] = t = YearTracker(year, self._date)
            return t

    def add(self, item, n=1):
        self._date_check()
        self._current.add(item, n)
        self._current.save_data()

    def subtract(self, item, n=-1):
        self._date_check()
        self._current.subtract(item, n)
        self._current.save_data()

    def get(self, item, month=None, year=None) -> TrackedResult:
        self._date_check()
        if year is not None: return self._get_tracker(year).get(item, month)

        res, m = 0, None
        for y in self._list_years():
            item = self._get_tracker(y).get(item, month)
            res += item.data
            m = item.month
        return TrackedResult(data=res, month=m, year=None, read_only=False)

    def counter(self, month=None, year=None) -> TrackedResult:
        self._date_check()
        if year is not None: return self._get_tracker(year).counter(month=month)

        res, m = Counter(), None
        for y in self._list_years():
            year = self._get_tracker(y).counter(month=month)
            res += year.data
            m = year.month
        return TrackedResult(data=res, month=m, year=None, read_only=False)

    _sort_types = {"name": lambda item: item[0], "count": lambda item: -item[1]}
    def list(self, sort="count", month=None, year=None, reverse=False) -> TrackedResult:
        """
         Lists all songs with given sorted order with an optional filter, current supported sortings: name,count
         Returns a sorted list with items in the form (name,count)
        """
        res = self.counter(month=month, year=year)
        return TrackedResult(data=sorted(res.data, key=self._sort_types[sort], reverse=reverse), *res[1:])

song_tracker = SongTracker()

class SongTrackerWindow(pywindow.PyWindow):
    window_id = "song_statistics"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.window_id)
        self.title = "Song statistics"

    def create_widgets(self):
        self.add_element("lbl", element_class=pyelement.PyTextLabel).text = "Pick a date"
        self.add_element("data", element_class=pyelement.PyCalendarInput, row=1)