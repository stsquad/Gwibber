import unittest, gettext, mx.DateTime
from gwibber import microblog

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(GenerateTimeStringTestCase)

# TODO should probably force locale to english before testing
class GenerateTimeStringTestCase(unittest.TestCase):
    def setUp(self):
        self.now = mx.DateTime.gmt()
        self.generate_time_string = microblog.support.generate_time_string

    def testonesecond(self):
        time_string = self.generate_time_string(self.now - mx.DateTime.oneSecond)
        self.assertEqual(time_string, '1 second ago')

    def testtwoseconds(self):
        time_string = self.generate_time_string(self.now - 2 * mx.DateTime.oneSecond)
        self.assertEqual(time_string, '2 seconds ago')

    def testoneminute(self):
        time_string = self.generate_time_string(self.now - mx.DateTime.oneMinute)
        self.assertEqual(time_string, '1 minute ago')

    def testtwominutes(self):
        time_string = self.generate_time_string(self.now - 2 * mx.DateTime.oneMinute)
        self.assertEqual(time_string, '2 minutes ago')

    def testoneday(self):
        time_string = self.generate_time_string(self.now - mx.DateTime.oneDay)
        self.assertEqual(time_string, '1 day ago')

    def testtwodays(self):
        time_string = self.generate_time_string(self.now - 2 * mx.DateTime.oneDay)
        self.assertEqual(time_string, '2 days ago')

    def testoneweek(self):
        time_string = self.generate_time_string(self.now - mx.DateTime.oneWeek)
        self.assertEqual(time_string, '7 days ago')

    def testoneyear(self):
        time_string = self.generate_time_string(self.now - 365 * mx.DateTime.oneDay)
        self.assertEqual(time_string, '1 year ago')

    def testtwoyears(self):
        time_string = self.generate_time_string(self.now - 2 * 365 * mx.DateTime.oneDay)
        self.assertEqual(time_string, '2 years ago')
