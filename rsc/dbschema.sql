CREATE TABLE series( title varchar(255) primary key, episodes integer, last_update DATE);
CREATE TABLE watchlist(chatid varchar(255), title varchar(255), PRIMARY KEY(chatid,title), FOREIGN KEY(title) REFERENCES series(title) ON UPDATE CASCADE ON DELETE CASCADE);
CREATE TRIGGER update_date AFTER UPDATE ON series
FOR EACH ROW
BEGIN
UPDATE series SET last_update=date('now') WHERE rowid = new.rowid;
END;
CREATE TRIGGER add_date AFTER INSERT ON series
FOR EACH ROW
BEGIN
UPDATE series SET last_update=date('now') WHERE rowid = new.rowid;
END;
