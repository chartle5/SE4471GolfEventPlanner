export const artifacts = {
  welcomePamphlet: {
    title: 'Welcome to the Spring Invitational 2026',
    content: [
      'Welcome message and sponsor acknowledgements.',
      'Course map and check-in locations.',
      'Emergency contacts and weather procedures.'
    ]
  },
  schedule: {
    title: 'Tournament Schedule & Itinerary',
    rows: [
      { time: '07:00', activity: 'Volunteer check-in' },
      { time: '07:45', activity: 'Player registration opens' },
      { time: '08:30', activity: 'Shotgun start' },
      { time: '13:30', activity: 'Lunch & scoring' },
      { time: '15:00', activity: 'Awards ceremony' }
    ]
  },
  email: {
    subject: 'Pre-Event Information — Spring Invitational 2026',
    body: 'Dear Participant,\nPlease find attached your tee time and pre-event instructions.'
  },
  rulesSheet: {
    title: 'Tournament Rules and Guidelines',
    sections: [
      { h: 'Format', p: '4-person scramble. Best ball per hole.' },
      { h: 'Scoring', p: 'Gross scores, nearest-to-pin contests.' }
    ]
  },
  faq: {
    title: 'FAQ',
    qas: [
      { q: 'What time do we arrive?', a: 'Registration opens at 7:45am.' },
      { q: 'Are carts allowed?', a: 'Limited carts — reserved for accessibility.' }
    ]
  }
}
