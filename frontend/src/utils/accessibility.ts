/**
 * Accessibility utilities for WCAG 2.1 Level AA compliance
 */

// Keyboard navigation keys
export const KEYS = {
  ENTER: 'Enter',
  SPACE: ' ',
  ESCAPE: 'Escape',
  TAB: 'Tab',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  HOME: 'Home',
  END: 'End'
} as const;

/**
 * Announce text to screen readers without visual display
 * @param message - Text to announce
 * @param priority - 'polite' for non-urgent, 'assertive' for urgent announcements
 */
export function announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;
  
  document.body.appendChild(announcement);
  
  // Remove after announcement
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}

/**
 * Handle keyboard navigation for interactive elements
 * @param event - Keyboard event
 * @param callback - Function to call on Enter or Space
 */
export function handleKeyboardNavigation(
  event: React.KeyboardEvent,
  callback: () => void
): void {
  if (event.key === KEYS.ENTER || event.key === KEYS.SPACE) {
    event.preventDefault();
    callback();
  }
}

/**
 * Focus management utility for modals and dialogs
 */
export class FocusTrap {
  private focusableElements: HTMLElement[] = [];
  private firstElement: HTMLElement | null = null;
  private lastElement: HTMLElement | null = null;
  private previouslyFocusedElement: HTMLElement | null = null;

  constructor(private container: HTMLElement) {}

  activate(): void {
    this.previouslyFocusedElement = document.activeElement as HTMLElement;
    this.updateFocusableElements();
    
    if (this.firstElement) {
      this.firstElement.focus();
    }
    
    this.container.addEventListener('keydown', this.handleKeyDown);
  }

  deactivate(): void {
    this.container.removeEventListener('keydown', this.handleKeyDown);
    
    if (this.previouslyFocusedElement) {
      this.previouslyFocusedElement.focus();
    }
  }

  private updateFocusableElements(): void {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])'
    ].join(', ');
    
    this.focusableElements = Array.from(
      this.container.querySelectorAll<HTMLElement>(focusableSelectors)
    );
    
    this.firstElement = this.focusableElements[0] || null;
    this.lastElement = this.focusableElements[this.focusableElements.length - 1] || null;
  }

  private handleKeyDown = (event: KeyboardEvent): void => {
    if (event.key !== KEYS.TAB) return;
    
    this.updateFocusableElements();
    
    if (event.shiftKey) {
      // Shift + Tab
      if (document.activeElement === this.firstElement && this.lastElement) {
        event.preventDefault();
        this.lastElement.focus();
      }
    } else {
      // Tab
      if (document.activeElement === this.lastElement && this.firstElement) {
        event.preventDefault();
        this.firstElement.focus();
      }
    }
  };
}

/**
 * Get appropriate ARIA attributes for button states
 * @param options - Button state options
 */
export function getButtonAriaProps(options: {
  isPressed?: boolean;
  isExpanded?: boolean;
  isDisabled?: boolean;
  controls?: string;
  describedBy?: string;
}): Record<string, string | boolean> {
  const props: Record<string, string | boolean> = {};
  
  if (options.isPressed !== undefined) {
    props['aria-pressed'] = options.isPressed;
  }
  
  if (options.isExpanded !== undefined) {
    props['aria-expanded'] = options.isExpanded;
  }
  
  if (options.isDisabled) {
    props['aria-disabled'] = true;
  }
  
  if (options.controls) {
    props['aria-controls'] = options.controls;
  }
  
  if (options.describedBy) {
    props['aria-describedby'] = options.describedBy;
  }
  
  return props;
}

/**
 * Check if reduced motion is preferred
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Validate color contrast ratio (WCAG AA requires 4.5:1 for normal text, 3:1 for large text)
 * @param foreground - Foreground color (hex)
 * @param background - Background color (hex)
 */
export function checkColorContrast(foreground: string, background: string): {
  ratio: number;
  passesAA: boolean;
  passesAAA: boolean;
} {
  const getLuminance = (hex: string): number => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = (rgb >> 16) & 0xff;
    const g = (rgb >> 8) & 0xff;
    const b = (rgb >> 0) & 0xff;
    
    const [rs, gs, bs] = [r, g, b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  };
  
  const l1 = getLuminance(foreground);
  const l2 = getLuminance(background);
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  
  return {
    ratio: Math.round(ratio * 100) / 100,
    passesAA: ratio >= 4.5,
    passesAAA: ratio >= 7
  };
}

/**
 * Skip to main content - focuses main element or element with id
 * @param targetId - ID of element to focus (defaults to 'main')
 */
export function skipToMainContent(targetId: string = 'main'): void {
  const target = document.getElementById(targetId) || document.querySelector('main');
  
  if (target) {
    target.setAttribute('tabindex', '-1');
    target.focus();
    target.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
  }
}
