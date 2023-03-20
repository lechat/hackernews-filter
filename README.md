Aleksey's Hacker News/Lobsters Crap Filter
==

This is heavily reworked fork of Derek's Hackernews Crap Filter (see below)

I host it on my home server and have no plans to release it as a standalone website.

This code reads HN/Lobsters regularly and stores articles in redis. Then main app
reads it from redis and applies filter.

Derek's Hackernews Crap Filter
==

Manifesto
--

Do you like the technical articles that filter through Hacker News (http://news.ycombinator.com)?

Are you **really** tired of schmaltz and chaff like this?
- "This is a web page. It's made up of words." ... "OMG IT'S SO TRUE"
- "Why I'm Leaving Elon Musk"
- "How do I find a technical co-founder?"


No longer.
--

- Stick your most-hated buzzphrases in filter.txt.
- Terminal.app => Profiles => Advanced => [x] Set locale environment variables on startup
- Run hn_filter.py in a terminal session.
- Or run hn_filter_server.py and visit http://localhost:31337/


But that's not all!
--

You also get my list of irritating buzzwords as a default filter set.  It slices, it dices, it kills monsters!

[Cmd]+Double-Click URLs in Mac OS X Terminal.app to open them.


Requirements
--

- Python 2.7 or Python 3.4
- Python modules: BeautifulSoup and Requests



Alternatives
--

There are other Hacker News filters (http://hnapp.com/) but they don't accommodate the level of grumpiness I have achieved (70+ entries in the default killfile).




Version History
--

v0.4 - 08-Nov-2014
- Add Python 3.x compatibility (tested with 3.4)
  (if you're on OS X, be sure to enable "Set locale environment variables on startup" in Terminal.app)
- HN is now all SSL, all the time, so enable SSL verification

v0.3 - 07-Sep-2013

- Bring back console version. Web version optional.
- Allow comments in killfile.
- Killfile updated with latest curmudgeonry.
- Clean up filenames.

v0.2 - 15-Aug-2013

- Use bottle.py to provide a web interface.  Contributed by tiberiu@tiberiuana.com (thank you)

v0.1 - 14-Aug-2013

- Initial release.



Have a nice day.
