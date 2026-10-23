"""No-network regression for ordered, bounded Ritsu Pocket lookahead."""
from unittest.mock import patch
import ritsu_say

def run():
    original="She smiles. The clock ticks! Is it working? Yes, it is."
    sentences=ritsu_say.sentence_chunks(original)
    assert sentences==["She smiles.","The clock ticks!","Is it working?","Yes, it is."]
    assert " ".join(sentences)==original
    assert len(ritsu_say.sentence_chunks("One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."))==10
    try:ritsu_say.sentence_chunks("x"*451)
    except ValueError:pass
    else:raise AssertionError("Sentence silently truncated")
    voice,delivered,events=[],[],[]
    class Trace:
        def record(self,event,seq=0,**details):
            events.append((event,seq,details))
    def client(method,path,body=None):
        if path=="/v1/speak":
            index=len(voice)+1
            voice.append(body["text"])
            return {"id":f"{index:032x}","state":"queued"}
        if path.startswith("/v1/jobs/"):
            return {"state":"completed","generation_seconds":1.1,"audio_seconds":3.2,"bytes":155000}
        if path=="/v1/deliver":
            index=int(body["job_id"],16)
            delivered.append(index)
            return {"state":"enqueued","relay_id":f"{index:024x}"}
        raise AssertionError(path)
    with patch("builtins.print"):
        result=ritsu_say.deliver_ordered(["Sentence "+str(i)+"." for i in range(1,11)],
                              "normal","test-turn-10-sent",client=client,trace=Trace())
    assert len(result)==10 and delivered==list(range(1,11))
    assert voice==["Sentence "+str(i)+"." for i in range(1,11)]
    pairs=[(event,seq) for event,seq,_ in events]
    assert pairs.index(("pocket_accepted",4))<pairs.index(("relay_deliver_start",1))
    assert pairs.index(("pocket_accepted",5))<pairs.index(("relay_deliver_start",1))
    assert [seq for event,seq,_ in events if event=="relay_enqueued"]==list(range(1,11))
    print("PASS no-network ten sentence integrity, four-way lookahead and FIFO relay")

if __name__=="__main__":
    run()
