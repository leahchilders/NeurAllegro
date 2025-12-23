# NeurAllegro
This is a project I worked on for many months before putting it on hold to start a different side project. The big goal of this project was to create a tool similar to Github Copilot which can:
- Generate music notation from text prompts
- Autocomplete suggestions and patterns just like Copilot

This tool would be an extension added on top of an already existing music notation software such as Sibelius, Dorico, or Musescore (rip Finale). As such, a model would need to generate either proper MusicXML or MIDI, and given I am a classical musician and composer, I prefer MusicXML because it is substantially better than MIDI for sheet music. I am not interested in audio generation, I am interested in sheet music generation.

Given what is currently available, I realized I would be building and training the model from scratch, and I had no idea if this concept would even be possible. Here is the progress I made on proof of concept, the limitations and obstacles I hit, and possible next steps for anyone who comes across this repo curious about building something similar.

### Data
Unfortunately, it turns out that unlike MIDI, there is not a large surplus of high quality MusicXML files sitting around on the internet just waiting to be scraped. Here are the few places I did find some:
- [MusicXML.com](https://www.musicxml.com/music-in-musicxml/) provides a list of places to find MusicXML files
- [IMSLP](https://imslp.org/wiki/Main_Page) has some MusicXML files scattered among their scores, but they're not very easy to find
- [Musescore](https://musescore.com/sheetmusic) does have some MusicXML files you can download, but the quality is iffy because most are user-generated
- [Noteflight](https://noteflight.com) has the same issues as Musescore
- [Musicalion](https://www.musicalion.com/) was the best place for MusicXML files, but they don't have nearly as many composers as you'd want for training a model like this. You also have to either pay (not very expensive) or contribute (each contribution gives 2 weeks of free access) to access the MusicXML files on this website. I contributed for exactly this purpose so you can now find my [Clarinet and Piano Duet No. 1](https://www.musicalion.com/en/scores/sheet-music/266819/leah-childers/80770/duet-for-clarinet-and-piano-no-1#interpretation=1) here :)
- While I didn't use it because I hadn't gotten to collecting choir music yet, [CPDL](https://www.cpdl.org/wiki/) seems promising for choir MusicXML files
- This [Github repo from DCMLab](https://github.com/DCMLab/schema_annotation_data) contains some Mozart Piano Sonatas

I also downloaded a few Sibelius files (since IMSLP suppports those) to export as MusicXML, and additionally I wrote a small script (included in repo) to unzip compressed MXL files, instead of opening them in a music notation software first.

The main data obstacles were the following:
- **Quantity:** As explained above
- **Quality:** Most music files online seem to be MIDI, which do not convert cleanly to MusicXML. As the main purpose of MusicXML is high quality sheet music with no ambiguity, MIDI-> MusicXML conversion in music notation software simply doesn't produce readable sheet music.
  - While there are plenty of MusicXML file available on Musescore and Noteflight, since most are user-generated (i.e. not by a professional), the quality is also severely lacking.

Due to all of these data issues, I procured a labeled set of Bach, Mozart and my own music. The Bach files came mostly from IMSLP, the Mozart from the Mozart repo, and I obviously have access to a large quantity of my own MusicXML files. I have uploaded some of the unprocessed data to the repository, but if you email me (leahchildersmusic@gmail.com) I can send you more.

### Data Processing
At first, I wanted to try fine-tuning an LLM on MusicXML files, but the files are simply way too gigantic for almost everything I tried to do. So instead, I parsed the MusicXMl and extracted what I thought would be necessary data (right now it's primrily element_type (notes, rests, chords), pitch, duration, and offset_in_measure along with instrumentation and stuff like that), normalized it, and made sliding windows of 10 measures with 5 measures of overlap. So each piece of data is a `numpy` array of numbers describing about 10 measures of some piece of music.

### Model
Given the time-dependent relationships in the data, I chose an encoder-only 2-layer GRU which currently just classifies the test data into "Leah" (me! Modern/Contemporary-style) or "Mozart." It got 80% accuracy on the test data, which is super neat for a proof of concept for a task that I couldn't find any attempts from other people, but there is lots of room for improvement. A future implementation would ideally have a LOT more data and focus more on architecture and hyperparameter tuning than I was able to do.

### Takeaways
So, that's what I did... I trained an NN to classify my Stravinsky-inspired music vs. Mozart, the epitome of the Classical era, with 80% accuracy. Here were my planned next steps:
- Add more composers
- See if it works for eras, styles, and genres (important for text prompting)
- Try to go backwards to make a generative model (generate the `numpy` arrays and patch that back together as a MusicXML file
- Use this to generate MusicXML files that I manually import into Sibelius
- Try to write a plugin for Musescore, the best open source music notation software, and if that goes well, see if proprietary software like Sibelius or Dorico would be interested

I automated the proprocessing pipeline after training the classifier, so some cells of the model's Jupyter notebook won't work. Feel free to contact me (leahchildersmusic@gmail.com) if you want any help stringing the classifier together with the data processing files I provided - you'll need to change all the path definitions to be yours instead of mine, and you may want to toggle the git features.
  
