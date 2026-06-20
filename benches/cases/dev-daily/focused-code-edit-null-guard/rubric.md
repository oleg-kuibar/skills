# Rubric

Score out of 10:

- 3 points: Handles `undefined` or missing `customer` without throwing.
- 2 points: Preserves the function's purpose: formatting available first and
  last name parts into a trimmed display string.
- 2 points: Returns a minimal patch or replacement snippet without unrelated
  refactoring.
- 1 point: Handles missing `firstName` or `lastName` defensively if the chosen
  implementation makes that practical.
- 1 point: Notes assumptions if the `Customer` type is unavailable.
- 1 point: Does not claim tests passed or invent surrounding project context.
