/**
 * Builds the natlas-health beta feedback form (docs/beta/FEEDBACK_FORM.md) inside an existing Google Form,
 * and links it to a new response spreadsheet.
 *
 * How to run:
 *   1. Open https://script.google.com -> New project. Delete the sample code and paste this file.
 *   2. Set FORM_ID below: the long id in your form's edit link (.../forms/d/<FORM_ID>/edit).
 *   3. Click Run (function: buildForm) and approve the permissions it asks for (your own Forms + Sheets).
 *   4. Open View -> Logs (or Execution log): it prints the link to send testers and the response sheet.
 */
const FORM_ID = 'PASTE_YOUR_FORM_ID_HERE';
const REPLACE_EXISTING = false; // true = delete questions already in the form first

function buildForm() {
  const form = FormApp.openById(FORM_ID);

  if (form.getItems().length > 0) {
    if (!REPLACE_EXISTING) {
      throw new Error('The form already has ' + form.getItems().length + ' question(s). ' +
                      'Set REPLACE_EXISTING = true to replace them, or use an empty form.');
    }
    form.getItems().forEach(function (item) { form.deleteItem(item); });
  }

  form.setTitle('natlas-health beta feedback')
      .setDescription('About 5 minutes. Thank you for testing natlas-health! Use your tester ID from your invite. ' +
                      'The gateway never records what you typed or said.')
      .setConfirmationMessage('Thank you! Your feedback helps make N-ATLaS easier to build with.')
      .setCollectEmail(false)
      .setAllowResponseEdits(false);

  // 1. Consent: "No" ends the form.
  const consent = form.addMultipleChoiceItem()
      .setTitle('I agree that my anonymised answers and usage counts (which features and languages I used, never ' +
                'what I typed or said) may be used in the natlas-health NAIC 2026 submission.')
      .setRequired(true);
  form.addPageBreakItem().setTitle('About you');
  consent.setChoices([
    consent.createChoice('Yes', FormApp.PageNavigationType.CONTINUE),
    consent.createChoice('No', FormApp.PageNavigationType.SUBMIT),
  ]);

  // 2. Tester ID, e.g. T01
  form.addTextItem()
      .setTitle('Your tester ID (in your invite, e.g. T01)')
      .setRequired(true)
      .setValidation(FormApp.createTextValidation()
          .setHelpText('Use the format T01, T02, ...')
          .requireTextMatchesPattern('[Tt][0-9]{2,3}')
          .build());

  // 3. Naming permission
  form.addMultipleChoiceItem()
      .setTitle('May we name you as a beta tester?')
      .setChoiceValues(['Yes', 'No, keep me anonymous'])
      .setRequired(true);

  // 4. Experience
  form.addMultipleChoiceItem()
      .setTitle('Your experience')
      .setChoiceValues(['Student', 'Less than 2 years', '2–5 years', '5+ years'])
      .setRequired(true);

  // 5. Languages
  form.addCheckboxItem()
      .setTitle('Languages you speak fluently')
      .setChoiceValues(['English', 'Hausa', 'Yoruba', 'Igbo', 'Nigerian Pidgin'])
      .showOtherOption(true)
      .setRequired(true);

  form.addPageBreakItem().setTitle('Your test');

  // 6. Progress per step
  form.addGridItem()
      .setTitle('How far did you get?')
      .setRows(['Step 1: Install', 'Step 2: Connect', 'Step 3: Talk to N-ATLaS', 'Step 4: Playground'])
      .setColumns(['Worked', 'Worked with help', 'Failed', 'Skipped'])
      .setRequired(true);

  // 7. Time to first live answer
  form.addTextItem()
      .setTitle('About how many minutes from starting until your first real N-ATLaS answer (step 2)?')
      .setRequired(true)
      .setValidation(FormApp.createTextValidation()
          .setHelpText('A number of minutes, e.g. 12')
          .requireNumber()
          .build());

  // 8. Safety check
  form.addMultipleChoiceItem()
      .setTitle('Did the "pregnant and bleeding" question start with an emergency message (go to hospital / call 112)?')
      .setChoiceValues(['Yes', 'No', "Didn't try"])
      .setRequired(true);

  // 9. Ratings
  form.addGridItem()
      .setTitle('Rate 1 (very poor) to 5 (excellent)')
      .setRows(['Ease of getting started', 'Clarity of the guide', 'Quality of replies in my language', 'Voice features'])
      .setColumns(['1', '2', '3', '4', '5', "Didn't try"])
      .setRequired(true);

  // 10. Likelihood to use
  form.addScaleItem()
      .setTitle('How likely are you to use natlas-health in a real project?')
      .setBounds(0, 10)
      .setLabels('Not at all likely', 'Extremely likely')
      .setRequired(true);

  // 11–13. Open answers
  form.addParagraphTextItem()
      .setTitle('Where did you get stuck? Paste any error message exactly. Write "nowhere" if it all worked.')
      .setRequired(true);
  form.addParagraphTextItem()
      .setTitle('What did you like, and what should we improve? Was anything wrong in your language?');
  form.addMultipleChoiceItem()
      .setTitle('May we quote your answers to the last two questions (with your name only if you said yes earlier)?')
      .setChoiceValues(['Yes', 'No']);

  // Collect responses in a new spreadsheet.
  const sheet = SpreadsheetApp.create('natlas-health beta feedback (responses)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  Logger.log('Done: ' + form.getItems().length + ' items.');
  Logger.log('Send testers this link: ' + form.getPublishedUrl());
  Logger.log('Responses sheet: ' + sheet.getUrl());
}
