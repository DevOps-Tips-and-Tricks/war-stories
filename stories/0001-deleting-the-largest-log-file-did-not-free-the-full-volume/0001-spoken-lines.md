# Episode 01 — Lines to say word for word

Everything else in the episode you improvise. These are the sentences where a wrong
word changes the meaning, so they are written out and meant to be said as written.

Keep this open next to the script while recording. If a take goes sideways, come back
to the line and start the paragraph again — don't paraphrase your way out of it.

All of them are short on purpose. Short sentences are easier to say under a camera and
easier to follow for a viewer whose English is also a second language.

---

## 1. The promise — first 20 seconds

> df says the disk is full.
> du says it's half empty.
> Neither of them is broken. They are answering two different questions.
> And the gap between those two questions is where production outages live.

Do not add anything before this. No greeting, no channel intro.

---

## 2. Act 1 — plant the open-once line

Say this while the writer script is on screen:

> This line opens the file one time, and keeps it open for as long as the process
> runs. That is what most real services do.
> Remember this line.

Say nothing about why it matters. That is the payoff in Beat 2 — explaining it here
gives the answer away before the panes diverge.

---

## 3. Beat 1 — the first rotation

> Watch what just happened. The file was renamed, and a fresh empty one was created
> at the old path.
>
> rename is a directory operation. It never touches the inode.
>
> So the process followed the rename without noticing — because it never had the name.
> It had the inode.

Then, pointing at df and du:

> These two still agree. Everything looks healthy. It is already broken.

---

## 4. Beat 2 — the divergence

**This is the one to rehearse.** It runs about 50 seconds and it carries the whole
episode. Say it over the simulator, not over a frozen terminal.

> Watch the top number and the bottom number. df is going up. du is not moving.
>
> Here is why.
>
> A filename is not a file. A directory is just a table — it maps names to inode
> numbers. The inode is what owns the data blocks.
>
> du walks the directory tree and adds up what it finds. Our file has no name anymore,
> so du does not find it.
>
> df does not walk anything. It asks the filesystem how many blocks are allocated.
> And those blocks are still allocated.
>
> The kernel frees an inode when two things are true at the same time. The link count
> is zero, and no process has the file open.
>
> unlink did the first one. The process is still holding the second one.
>
> That is the line I asked you to remember. It opened the file one time.
> If it reopened the path on every write, none of this would happen.
>
> So right now, this data is unreachable and undeletable at the same time.
>
> And there it is. Disk full. Directory empty.

Breathe at every paragraph break. Those are the edit points if you need them.

---

## 5. Beat 3 — finding it

> +L1 means link count below one. Deleted, but still open — by definition.

On adding `-a`:

> The -a matters more than it looks. By default lsof ORs its filters together, so
> without it you get deleted files anywhere, plus everything on this mount. That is a
> longer list than you started with. -a turns it into AND.

On `/proc`:

> Every tool that finds this is a wrapper around slash proc, slash P-I-D, slash f-d.
> Remember this one. In the Kubernetes section, it is the only one left.

---

## 6. Beat 4 — truncate, and what did not change

Run the command first. Let the bar drop. Then:

> The space came back, and the process never noticed. That path points at the inode
> itself, so I truncated the real file through the descriptor.

Now point at the fd pane:

> Now look at this. It did not change.
>
> File descriptor 9 still shows the same deleted path. The link count is still zero.
> The inode is still an orphan.
>
> That is not the screen failing to update. That is the proof that this worked.
>
> truncate frees blocks. It does not touch the descriptor. If that entry had changed,
> I would have killed something.

Then the judgment call:

> Restarting the service also frees the space, and in most shops that is what actually
> gets done. The reason to reach for truncate is when a restart costs you something —
> a replica resync, a cold cache, requests in flight.

---

## 7. Beat 6 — the fix

> copytruncate copies the contents out, then empties the original in place. The inode
> never changes, so the descriptor stays valid.
>
> The cost is a race. Anything written between the copy and the truncate is lost. Fine
> for access logs. Not fine for anything you would audit.

> postrotate is the better fix when the app supports it. You rename the file, then send
> a signal, and the app closes the old file and opens the new one. No race, nothing lost.

**The landing line.** Say it slowly, then stop talking:

> If your rotation strategy does not tell the process that it happened, you have not
> rotated anything. You have renamed a file and lied to yourself.

---

## 8. The bridge into Act 3

> That is the toy version.
> I'm Milad. I build and run Kubernetes platforms for a living.
> Here is what this looked like on a cluster I run, where it took one member of a
> database replica set down.

This is the first time you say your name. Not earlier: before this point the viewer
has no reason to care who you are. Here they are about to hear a production story, and
the name is what makes it yours. Never add an employer or a client — it would
de-anonymise the incident.

---

## 9. The close — after the three moves

Say the three moves from the outline first. Then:

> That is what this channel is.
> Real incidents, the wrong guesses included, and one habit you can take to your own
> stack.
> If you have a war story where the first guess was wrong, send it to me.
> The repo is in the description.

Then name the next episode and stop. No "like and subscribe" — the ask for a war story
is the call to action.

---

## Words to slow down on

YouTube's auto-captions are a useful test here: upload the cut as unlisted, read the
generated transcript, and anywhere the machine mangled a word, a viewer probably
struggled with it too.

| word | say it as | note |
|---|---|---|
| inode | **EYE**-node | the most common mistake is "ih-NODE" |
| nlink | **N**-link | spell the n |
| fd | **eff-dee** | never "fuhd" |
| lsof | **ell-ess-oh-eff** | spelling it out is clearest |
| /proc | **slash prock** | |
| truncate | **TRUN**-kate | stress the first syllable |
| unlink | **un-LINK** | |
| allocated | **AL**-o-kay-ted | comes up a lot; worth a dry run |
| superblock | **SUPER**-block | |
| descriptor | **dis-KRIP-ter** | |
| orphan | **OR**-fun | |

"blocks still allocated" is the hardest phrase in the episode to say cleanly. Practise
it a few times, or split it: "those blocks are still allocated."

---

## Four things never to say

These are the usual ways this gets explained wrong. Each one costs you credibility with
exactly the viewer you want.

**"df is wrong"** or **"du is lying."** Neither tool is wrong — that is the entire
point of the episode. The title is a joke that the content then corrects. If you say it
straight, you have undercut your own thesis.

**"The file is locked."** Nothing is locked. There is no lock anywhere in this
mechanism. Say "the inode can't be freed yet" instead.

**"rm doesn't really delete the file."** rm always removes the name — that part always
works. Say "unlink removes the name. Freeing the data is a separate step with its own
condition."

**"The file is still there."** Too vague, and it is what makes people think the name
might come back. Say "the data is still there. The name is gone, and it is not coming
back."

---

## Before you record

- [ ] Read section 4 out loud three times, against a stopwatch
- [ ] Record the hardest 60 seconds once and delete it — it warms up your mouth
- [ ] Record Beat 2 twice in a row without watching the first take; keep the tighter one
- [ ] Leave the pauses in. Cutting every breath creates a worse rhythm than the breath did
