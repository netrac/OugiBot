# OugiBot
A pretty simple bot for Telegram that sends you a notification when a new episode from a seasonal anime series you follow is released.

### Commands:
- ```/add <name of the series>```: Looks for matches with the provided name and prompts you to add one from a list of four based on your search.
- ```/list```: Lists all series you've added so far.
- ```/remove <name of the series>```: Removes the requested series from your following list.

#### Dependencies:
This bot was made using the following dependencies:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot), a Python interface for the Telegram Bot API.
- [FuzzyWuzzy](https://github.com/seatgeek/fuzzywuzzy) for string matching.
- [Anitopy](https://github.com/igorcmoura/anitopy) for parsing chapters' filenames.

*In case the anime you're looking for doesn't show up while searching, send an email to [netracf@gmail.com](mailto:netracf@gmail.com). __Make sure__ you're searching for seasonal anime and not for one that's already fully released. They won't show up in the search.*

Hope you find it useful!
<br/>
<br/>
<p align="center">
<img src="https://i.imgur.com/TD0O72Q.gif">
</p>
