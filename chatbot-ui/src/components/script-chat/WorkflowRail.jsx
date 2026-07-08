import { SCRIPT_CHAT_STAGES, getStageIndex } from '../../lib/scriptChatContract';

export function WorkflowRail({ currentStage, isLoading }) {
  const activeIndex = getStageIndex(currentStage);

  return (
    <aside className="script-workflow-rail" aria-label="Script workflow progress">
      <div className="script-rail-header">
        <span className="script-eyebrow">Workflow</span>
        <strong>Script Chat</strong>
      </div>

      <ol className="script-stage-list">
        {SCRIPT_CHAT_STAGES.map((stage, index) => {
          const Icon = stage.icon;
          const isDone = activeIndex > index;
          const isActive = activeIndex === index;

          return (
            <li
              className={[
                'script-stage-item',
                isDone ? 'is-done' : '',
                isActive ? 'is-active' : '',
              ].filter(Boolean).join(' ')}
              key={stage.key}
            >
              <span className="script-stage-icon">
                <Icon size={16} aria-hidden="true" />
              </span>
              <span>{stage.label}</span>
              {isActive && isLoading && <span className="script-stage-pulse" />}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
