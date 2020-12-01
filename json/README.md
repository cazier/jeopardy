## json

In this directory are the human-readable versions of the scraped answer and question data. There are sub-directories
containing the data separated by a number of factors, all of which are pretty self-explanatory:
- `by_show` - split by show number
- `by_year` - split by the year the episode aired
- `by_round` - split by the round of Jeopardy! (Jeopardy!, Double Jeopardy!, etc.)
- `by_completion` - split by whether the scraping pulled a full round for that category or whether some sets are 
missing
- `by_external` - split by whether there is external content (i.e., a picture, audio, etc.)
- `by_limit` - split all the questions into files with a defined maximum (by default 50K) number of sets

To minimize the final file size, each file has a single letter describing the answer/question set's information as
follows:
- `c` - **C**ategory
- `d` = Air **D**ate
- `a` = **A**nswer
- `v` = **V**alue
- `q` = **Q**uestion
- `r` = **R**ound
- `s` = **S**how Number
- `e` = Has **E**xternal Media
- `f` = Complete Category (i.e., it's **F**ull)

Finally, there is also the `clues.json` file which is a single file with all of the answer/question sets in a single
file. This is what's used to make the sqlite database.

<!-- Fortunately, with compression, all of this "data" is really just approximately the size of the single `clues.json` file! -->