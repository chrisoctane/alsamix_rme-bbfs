A configurable mixer and patchbay for ALSA devices. The idea is that "ALSAMix_RME" finds every control exposed by an RME audio interface and lists them as "blocks" in the Patchbay. You can then connect channels together in pannable pairs of dual mono/ stereo groups of any channels which populate the output "tabs" where your custom mixer is built. Save the configs as 'Layouts' and you can have custom mixers at hardware level. Yippee.

It's for Linux and ALSA and initially aimed at RME interfaces in class compliant mode (which exposes the channels to ALSA). You'll need to install Python.

Navigate to the folder and run:

python3 main.py

from your terminal.

Help and advice is more than welcome :)
