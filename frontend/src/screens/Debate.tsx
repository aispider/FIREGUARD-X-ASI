import { Panel, Tag } from '../components/ui';
import { useMission } from '../state/mission';

export function Debate() {
  const { result } = useMission();
  if (!result) return <div className="skel">Waiting for the council…</div>;
  return (
    <Panel title="AI debate" sub="Built from the council's structured findings. Citations point to evidence IDs.">
      <div className="chat">
        {result.debate.map((m, i) => (
          <div key={i} className={`msg ${m.speaker}`}>
            <div className="who"><i /><span className="lbl">{m.label}</span></div>
            <p>{m.text}</p>
            <div className="cites">{m.citations.map((c) => <Tag key={c}>{c}</Tag>)}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
