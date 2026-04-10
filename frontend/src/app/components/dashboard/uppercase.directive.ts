import { Directive, HostListener } from '@angular/core';
import { NgControl } from '@angular/forms';

@Directive({ selector: '[appUppercase]', standalone: false })
export class UppercaseDirective {
  constructor(private control: NgControl) {}

  @HostListener('input', ['$event'])
  onInput(event: Event) {
    const input = event.target as HTMLInputElement;
    const start = input.selectionStart ?? 0;
    const end = input.selectionEnd ?? 0;
    input.value = input.value.toUpperCase();
    input.setSelectionRange(start, end);
    this.control.control?.setValue(input.value, { emitEvent: false });
  }
}
