import { cn } from '@/lib/utils';
import { NoiseBackground } from './noise-background';

const GRADIENTS = {
  blue: ['rgb(45, 62, 142)', 'rgb(74, 91, 168)', 'rgb(242, 101, 34)'],
  orange: ['rgb(242, 101, 34)', 'rgb(255, 130, 70)', 'rgb(45, 62, 142)'],
  muted: ['rgb(227, 227, 221)', 'rgb(234, 234, 229)', 'rgb(210, 216, 226)'],
};

function NoiseBackgroundButton({
  children,
  className,
  disabled,
  gradient = 'blue',
  type = 'button',
  ...props
}) {
  return (
    <NoiseBackground
      animating={!disabled}
      className="noise-action-shell-content"
      containerClassName={cn(
        'noise-action-shell',
        `noise-action-shell-${gradient}`,
        disabled && 'noise-action-shell-disabled',
        className,
      )}
      gradientColors={GRADIENTS[gradient] || GRADIENTS.blue}
      noiseIntensity={disabled ? 0.12 : 0.24}
      speed={0.08}
    >
      <button
        className={cn(
          'noise-action-button',
          `noise-action-button-${gradient}`,
          disabled && 'noise-action-button-disabled',
        )}
        disabled={disabled}
        type={type}
        {...props}
      >
        {children}
      </button>
    </NoiseBackground>
  );
}

export { NoiseBackgroundButton };
