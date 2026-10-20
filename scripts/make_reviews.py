"""Writes data/reviews.csv: 108 fictional product reviews shaped like a Yotpo export
plus Amazon and independent-site rows. Every review is invented. The themes and
their mix follow what public AlgaeCal reviews talk about (results on a scan,
stomach tolerance, price, pill size, shipping, support, subscription). The rise
in price complaints over the last three weeks is planted on purpose, so the
dashboard has something to surface; the README says so."""
import csv, random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(11)
ROOT = Path(__file__).resolve().parent.parent
# (stars, product, theme, title, body)
R = [
(5,"AlgaeCal Plus","results","T-score moved for the first time in years","My DEXA in March was -2.8 at the spine. Eighteen months on Plus and Strontium Boost and it read -2.3. My doctor asked what I had changed. I had not expected to write a review for a supplement but here we are."),
(5,"AlgaeCal Plus","results","Stable, which for me is a win","I am 71. My scans had dropped every two years since menopause. The last one was unchanged from the one before. Unchanged is the best news I have had from that machine."),
(4,"AlgaeCal Plus","results","Small improvement at the hip","Hip went from -2.1 to -1.9, spine the same as before. Not dramatic but it is the right direction. Four stars because it took a full year and the price adds up."),
(1,"AlgaeCal Plus","results","Nothing changed in two years","Two years, every capsule, and my scan is exactly where it was. I am glad it did not get worse but that is a lot of money for exactly the same number."),
(2,"AlgaeCal Basic","results","Scan got worse","Took Basic for fourteen months. Spine down from -2.4 to -2.7. The consultant was kind on the phone and explained the guarantee, but I am still disappointed."),
(5,"Strontium Boost","results","Consultant warned me about the scan reading","I called to ask why my scan jumped so much. The consultant explained that strontium changes how the machine reads bone and told me not to over-read the number. Honest answer, which I did not expect."),
(5,"AlgaeCal Plus","results","Doctor was surprised","Went from osteoporosis range to osteopenia range at the hip after a year and a half. My GP does not believe in supplements and even she said keep doing whatever you are doing."),
(3,"AlgaeCal Plus","results","Too soon to tell","Six months in. No scan yet so I cannot say if it works. No side effects at all, swallowing is fine. Will update after the DEXA in January."),
(4,"AlgaeCal Plus","results","Second scan held steady","First scan after a year was flat. I was annoyed, then my consultant pointed out flat is what we were hoping for at my age, 78. Fair enough."),
(1,"AlgaeCal Plus","results","Guarantee was harder than the ad made it sound","My scan was worse and I asked for the money back. They wanted the before and after scans on the same machine, and mine were at two clinics. Took three calls. I did eventually get it but I would not call it easy."),
(5,"AlgaeCal Plus","results","-3.1 to -2.6","Spine -3.1 to -2.6 in 20 months. Also take vitamin K2 and walk daily so I cannot give all the credit to one bottle, but I am not stopping."),
(2,"AlgaeCal Basic","results","No change, cancelling","A year on Basic. Same T-score to the decimal. I am cancelling the subscription. The product may work for others, it did not for me."),
(4,"AlgaeCal Plus","results","Better than the prescription did","I came off a bisphosphonate because of jaw worries. Two years of Plus and my numbers are slightly better than when I was on the drug. Four stars only because of the cost."),
(5,"AlgaeCal Plus","results","Forearm scan improved","Had a forearm DEXA because of a hip replacement. Improved from -2.6 to -2.2. The consultant actually knew what a forearm scan was, which my pharmacist did not."),
(1,"Strontium Boost","results","Reading went up, then my doctor explained why","My scan jumped a whole point and I was thrilled, then my endocrinologist told me strontium inflates the reading. I feel misled. The website should say this more clearly."),
(3,"AlgaeCal Plus","results","Mixed scan","Spine better, hip slightly worse. The consultant said that happens. I do not know what to think so three stars until the next one."),
(5,"AlgaeCal Plus","results","Three scans, three improvements","2022 -2.9, 2024 -2.5, 2026 -2.2. Same clinic, same machine. That is all I need to know."),
(2,"AlgaeCal Plus","results","Expected more after the testimonials","The stories on the site are all big jumps. Mine was -2.5 to -2.4 after 18 months. Maybe that is realistic but the marketing sets you up for more."),
# side effects / tolerance
(5,"AlgaeCal Plus","side_effects","Finally a calcium I can tolerate","Every other calcium gave me constipation within a week. Three months on this and nothing. I take two with breakfast and two with dinner as the box says."),
(1,"AlgaeCal Plus","side_effects","Nausea every morning","Felt sick within half an hour of the morning dose for two weeks running. Tried with food, tried less, no difference. Returned the rest. Your stomach may differ."),
(2,"AlgaeCal Basic","side_effects","Bloating","Bloated and uncomfortable from day three. Stopped after the first bottle. Customer service offered tips about splitting the dose but it did not help me."),
(4,"AlgaeCal Plus","side_effects","Mild stomach upset that passed","First ten days my stomach grumbled. Then it settled and now I notice nothing. Would have given five if the box had warned me it can take a while."),
(5,"AlgaeCal Plus","side_effects","No more heartburn","Switched from calcium carbonate which gave me heartburn every night. Gone. Whatever the algae does differently, my stomach approves."),
(3,"AlgaeCal Plus","side_effects","Constipation unless I drink a lot","Works out if I drink two extra glasses of water. Forget the water and I pay for it. Three stars because it needs managing."),
(1,"Strontium Boost","side_effects","Headaches","Started getting headaches a week into Strontium Boost. Stopped, they went. Started again, they came back. Stopped for good. Plus on its own is fine."),
(2,"AlgaeCal Plus","side_effects","Upset stomach, could not finish bottle","Cramping after the evening dose. I am 80 and did not want to push through it. The return was handled quickly, I will say that."),
(4,"AlgaeCal Plus","side_effects","Easy on the stomach, hard on the wallet","Zero digestive issues, which for me is remarkable. Docking a star for the price, which is the only thing about it that hurts."),
(5,"AlgaeCal Basic","side_effects","Gentle","I have IBS and was nervous. No flare, no cramps. I take it with meals as advised."),
(2,"AlgaeCal Plus","side_effects","Metallic taste","Odd metallic taste for an hour after each dose. Not unbearable, but enough that I dread it. Two stars."),
(3,"AlgaeCal Plus","side_effects","Kidney stone worry","I have had kidney stones and my urologist was not keen on more calcium. The consultant said to talk to my doctor rather than giving me an answer. I appreciated that but I still do not know if I should take it."),
# price / value
(2,"AlgaeCal Plus","price","Price went up again","Second increase in a year. I am on a fixed income. I believe in the product but I cannot keep absorbing this. Looking at alternatives."),
(1,"AlgaeCal Plus","price","Too expensive for what it is","Over eighty dollars a bottle. It is calcium from algae with vitamin D and K. I wanted it to be worth it. For me it is not."),
(3,"AlgaeCal Plus","price","Works, costs a fortune","Scan improved so I cannot complain about the product. I can complain about the price. Buying the six-month pack is the only way it is bearable."),
(2,"AlgaeCal Plus","price","Subscribe and Save is not much of a save","Ten percent off when the base price is this high is not a saving, it is a rounding error. Cancelling and buying the bulk pack when there is a sale."),
(4,"AlgaeCal Plus","price","Worth it, barely","It is doing what it says. I just wish I did not have to choose between this and other things each month."),
(1,"AlgaeCal Plus","price","Price increase email was the last straw","Got the email about the new price the same week my pension did not go up. Cancelled. I may come back if there is ever a real sale."),
(2,"Strontium Boost","price","Expensive add-on","Plus is already dear and then they tell you that you really need Strontium Boost too. Together it is more than my electricity bill."),
(3,"AlgaeCal Basic","price","Reasonable only in bulk","Monthly price is steep. The six-month pack brings it down enough that I kept going. Would not buy one bottle at a time again."),
(2,"AlgaeCal Plus","price","Costs more than my prescription did","My old prescription was covered. This is not. I understand why it is not, but the gap is a lot and it keeps growing."),
(1,"AlgaeCal Plus","price","Cannot justify the latest increase","Been a customer four years. The product has not changed. The price has, twice. I feel like loyalty counts for nothing."),
(4,"AlgaeCal Plus","price","Got a discount by asking","Called to cancel over the price and the consultant found me a better plan. Staying for now. It should not take a phone call though."),
(2,"AlgaeCal Plus","price","Shipping on top of the price","Eighty something for the bottle and then shipping on top unless you buy more. The total surprised me at checkout."),
(3,"AlgaeCal Plus","price","Pricey but I trust it","I do not love paying this much. I do trust the company more than the cheap brands. Three stars is where those two feelings meet."),
(1,"AlgaeCal Plus","price","Not for people on a pension","I am sure it is good. It is also priced for people who are not me. Cancelled after two bottles."),
(2,"AlgaeCal Plus","price","Why did my price change","My renewal went up without me noticing until the card statement. Yes there was an email, no I did not read it. The jump was still unwelcome."),
# pill size / taking it
(2,"AlgaeCal Plus","pills","Capsules are huge","Four large capsules a day. I had a stroke and swallowing is hard. I open them into yogurt which works but is a nuisance."),
(4,"AlgaeCal Plus","pills","Big, but manageable with a drink","They are large. With a full glass of water they go down. Would love a smaller capsule even if it meant more of them."),
(3,"AlgaeCal Basic","pills","Four a day is a lot to remember","Twice a day with meals. I forget the dinner dose at least twice a week. A once-daily option would suit me better."),
(1,"AlgaeCal Plus","pills","Could not swallow them","Tried for a week. Gagged every time. My daughter opens them for me now. Not the product's fault entirely but a smaller pill would help a lot of us."),
(5,"AlgaeCal Plus","pills","Fine for me","Reading the other reviews I expected horse pills. They are large but no worse than my fish oil. No trouble."),
(3,"AlgaeCal Plus","pills","Smell","Capsules have a seaweed smell when you open the bottle. Fine once swallowed. Just a heads up."),
(4,"AlgaeCal Plus","pills","Powder in a smoothie works","I open them into a morning smoothie. Consultant confirmed that is fine. Taste is barely there."),
(2,"AlgaeCal Plus","pills","Too many pills with everything else","With my other medications I am up to eleven pills a day. Adding four more was the tipping point. Went down to two a day and I know that is not the full dose."),
# shipping
(1,"AlgaeCal Plus","shipping","Package stuck for two weeks","Tracking said it left the warehouse and then nothing for twelve days. I ran out. Support sent a replacement eventually but I missed almost two weeks of doses."),
(2,"AlgaeCal Plus","shipping","Wrong item sent","Ordered the Bone Builder Pack, got collagen. They fixed it but I had to pay return shipping first and claim it back."),
(4,"AlgaeCal Plus","shipping","Fast to Ontario","Four days to Ontario. Box was fine. The customs form was correct which has not been my experience with other US supplements."),
(2,"AlgaeCal Plus","shipping","Delivery to UK took a month","A month to the UK plus a customs charge I was not warned about. The product is fine, the journey was not."),
(5,"AlgaeCal Plus","shipping","Arrived early","Ordered Monday, here Thursday. Nothing to add."),
(3,"AlgaeCal Plus","shipping","Bottle arrived with a broken seal","Outer box was fine, inner seal was broken. They replaced it without fuss. Three stars because it should not happen."),
(1,"AlgaeCal Plus","shipping","Lost in the post, slow replacement","First order never arrived. Took a week of emails to get a replacement sent. Second one came fine. Not a good first impression."),
(4,"AlgaeCal Basic","shipping","Reliable monthly delivery","Subscription box shows up like clockwork every month. Only wish the delivery date were adjustable from the account page."),
# support / consultants
(5,"AlgaeCal Plus","support","The consultant actually listened","I called in tears after a bad scan. The consultant spent half an hour with me, did not push product, and told me to see my doctor about one thing I mentioned. That is rare."),
(5,"AlgaeCal Plus","support","Best customer service I have dealt with","Email answered the same day, by a person who clearly read what I wrote. I have cancelled subscriptions over worse service than this. Staying."),
(2,"AlgaeCal Plus","support","Took three emails to get an answer","Asked a simple question about taking it with thyroid medication. First two replies were generic. Third one was helpful. Should have been one."),
(4,"AlgaeCal Plus","support","Helpful but scripted at first","First call felt like reading from a card. Once I pushed back she dropped the script and was genuinely helpful. Four stars."),
(5,"Strontium Boost","support","Told me to check with my doctor","Asked about Strontium Boost with a heart condition. Consultant would not give medical advice and told me to ask my cardiologist. Correct answer. Respect for that."),
(1,"AlgaeCal Plus","support","No reply for a week","Sent an email about a double charge. Nothing for seven days. Then a reply asking for details I had already given. Sorted in the end but it should not be this hard."),
(5,"AlgaeCal Plus","support","Followed up without being asked","Consultant called back two weeks after my first call to ask how I was getting on with the dose. Nobody does that any more."),
(3,"AlgaeCal Plus","support","Nice people, long wait","Phone wait was twenty minutes. The person was lovely. The wait was not."),
(4,"AlgaeCal Plus","support","Patient with my questions","I asked a lot of questions about the research. The consultant answered what she could and sent links for the rest. Did not pretend to know what she did not."),
(2,"AlgaeCal Plus","support","Felt like a sales call","Called with a question, left with a pitch for Strontium Boost and the six-month pack. I just wanted my question answered."),
# subscription / billing
(1,"AlgaeCal Plus","subscription","Charged twice this month","Two charges on my card for one bottle. Still waiting for the second one to be refunded. The product is fine, the billing is not."),
(2,"AlgaeCal Plus","subscription","Hard to cancel","Could not find cancel in the account page. Had to email. Took two days. There should be a button."),
(4,"AlgaeCal Plus","subscription","Easy to pause","Paused for two months while I travelled. One email, done. Restarted on time."),
(1,"AlgaeCal Plus","subscription","Renewed after I cancelled","Cancelled in September, charged in October. They refunded it, but I had to notice it first. Check your statements."),
(3,"AlgaeCal Plus","subscription","Reminder email went to spam","Got charged for a renewal I forgot about. The reminder was in my spam folder. Not entirely their fault but a text would help."),
(2,"AlgaeCal Basic","subscription","Switched to Plus, got billed for both","Asked to switch from Basic to Plus and got billed for both one month. Fixed after a call, but annoying."),
(5,"AlgaeCal Plus","subscription","Subscription just works","Eighteen months, never a billing problem, never a missed delivery. Boring in a good way."),
(2,"AlgaeCal Plus","subscription","Cannot change delivery date online","Every month I have to email to move the delivery a week. The account page should let me do this."),
(1,"AlgaeCal Plus","subscription","Debit card charged, overdraft fee","They say do not use a debit card and now I know why. Renewal hit before my pension and I got an overdraft fee. That is on me partly, but the warning is buried."),
(4,"AlgaeCal Plus","subscription","Refund for the double charge came quickly","Double charged, emailed, refunded in three days with an apology. Mistakes happen, this was handled well."),
# more results / mixed to fill
(5,"AlgaeCal Plus","results","Two years, both scans up","Both hip and spine improved over two years. My rheumatologist asked for the brand name."),
(4,"AlgaeCal Plus","results","Modest gain, no side effects","-2.3 to -2.1 after a year. Not huge. But no drug side effects either, which is why I am here."),
(2,"AlgaeCal Plus","results","Same as before","Twelve months, same reading. Keeping going one more year because stable is better than falling, but I am not thrilled."),
(5,"AlgaeCal Plus","results","Osteopenia to normal at the hip","Hip went from -1.3 to -0.9 at 63. I am in the normal range for the first time since I was tested."),
(3,"AlgaeCal Basic","results","Not sure it is doing anything","No scan since I started, no way to know. Taking it on faith for now."),
(1,"AlgaeCal Plus","results","Worse, and I did everything right","Took it exactly as directed for 18 months. Spine down 0.3. The guarantee process has started but I would rather have had the result."),
(4,"AlgaeCal Plus","side_effects","Took a month to settle","Stomach complained for the first month. Now fine. Hang in there if you can."),
(5,"AlgaeCal Plus","side_effects","No constipation at all","Switched from a supermarket calcium because of constipation. Problem solved on day one."),
(2,"AlgaeCal Plus","price","Great product, wrong price","If this cost half as much I would give it five stars and buy it for my sister. At this price I am not even sure I can keep buying it for me."),
(1,"AlgaeCal Plus","price","Another increase","Just saw the new price at renewal. That is three increases since I started. Cancelling today."),
(3,"AlgaeCal Plus","price","Buy on sale or not at all","I only reorder when there is a sale. Full price is out of reach. Works though."),
(2,"AlgaeCal Plus","price","Price increase with no explanation","The email just said prices are changing. No reason. For a company that talks about trust, that felt thin."),
(1,"AlgaeCal Plus","price","Cancelled over cost","Loved the product. Could not afford the new price. Cancelled. Will miss it."),
(4,"AlgaeCal Plus","pills","Take them with dinner and they are fine","Large but fine with a meal. Empty stomach is a mistake, learn from me."),
(2,"AlgaeCal Plus","shipping","Box crushed","Box arrived crushed, one bottle cracked. Replacement sent. Pack them better."),
(5,"AlgaeCal Plus","support","Real human on the first ring","Phone answered by a person on the first ring who knew the product. I am not used to that."),
(3,"AlgaeCal Plus","support","Good advice, slow email","The advice was good when it came. Two days per reply is slow when you are worried."),
(1,"AlgaeCal Plus","subscription","Three bottles I did not order","Somehow my subscription was set to three bottles a month. Charged for all three. Refund took two weeks."),
(4,"AlgaeCal Plus","subscription","Skipping a month is easy by email","Needed to skip a month. One email, sorted the same day. Would prefer to do it myself online."),
(2,"AlgaeCal Plus","price","Six-month pack is the only sane option","Monthly price is wild. Six-month pack is bearable. Why not just make the monthly price fair?"),
(1,"AlgaeCal Plus","price","Unaffordable now","Cannot do it any more at the new price. Three years a customer. Sorry."),
(3,"AlgaeCal Plus","price","Price is the only complaint","Product good. Service good. Price not good."),
(2,"AlgaeCal Plus","price","Raised the price, kept the shipping fee","Raise the price fine, but then at least include shipping. Both together is too much."),
]
assert len(R) >= 100, len(R)
FIRST = ["Margaret","Barbara","Linda","Patricia","Carol","Susan","Judith","Joan","Nancy","Dorothy","Sandra","Elaine","Marion","Ruth","Helen","Janet","Shirley","Beverly","Eileen","Gloria","Frances","Phyllis","Lorraine","Maureen","Yvonne","Brenda","Rosemary","Diane","Valerie","Pauline","Sheila","Norma","Doreen","Marjorie","Anita","Jeanne","Wendy","Christine","Lynda","Kathleen"]
LAST = ["H.","W.","P.","M.","K.","R.","S.","T.","B.","D.","L.","G.","F.","C.","N."]
SOURCES = ["Yotpo"]*6 + ["Amazon"]*3 + ["Independent site"]*1
start = datetime(2026, 8, 3)
rows = []
# dates: price complaints weighted to the last 3 weeks (planted trend, disclosed)
for i, (stars, product, theme, title, body) in enumerate(R):
    if theme == "price" and random.random() < 0.65:
        day = random.randint(49, 68)
    else:
        day = random.randint(0, 68)
    ts = start + timedelta(days=day, hours=random.randint(6, 21), minutes=random.randint(0, 59))
    src = random.choice(SOURCES)
    if src == "Independent site" and stars >= 4 and random.random() < 0.7:
        src = "Yotpo"
    rows.append({"id": f"R{i+1:03d}", "source": src, "posted_at": ts.strftime("%Y-%m-%d %H:%M"), "stars": stars, "product": product,
                 "reviewer": f"{random.choice(FIRST)} {random.choice(LAST)}", "verified": int(src != "Independent site" and random.random() < 0.85),
                 "title": title, "body": body, "theme": theme,
                 "sentiment": "negative" if stars <= 2 else ("neutral" if stars == 3 else "positive")})
rows.sort(key=lambda r: r["posted_at"])
out = ROOT / "data" / "reviews.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
import collections
print(len(rows), "reviews ->", out)
print(collections.Counter(r["theme"] for r in rows))
print(collections.Counter(r["source"] for r in rows))
print(collections.Counter(r["sentiment"] for r in rows))
