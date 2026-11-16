export const companies = {
  launchplan: { name: 'LaunchPlan', domain: 'launchplan.dev', url: 'https://launchplan.dev' },
  specflow: { name: 'SpecFlow', domain: 'specflowai.com', url: 'https://specflowai.com' }
};
export const shows = {
  town: { name:'Launch day', company:'launchplan', description:'The crew can only feature one idea this week. They open the choice to the LaunchPlan community and see what rises to the top.', episode:'Who gets the next spot?', image:'cafe.webp', alt:'Orange and sage robot friends talking at a miniature cafe.', caption:'Concept scene: the cafe where the crew reads the nominations.' },
  build: { name:'From idea to first build', company:'specflow', description:'Claude and the crew turn three readings of the same idea into one build they can test.', episode:'From idea to first build', image:'workshop.webp', alt:'Robot makers testing an idea together around a miniature workbench.', caption:'Concept scene: the crew puts its first build to the test.' }
};
export const formats = {
  story: { name:'Story spot', duration:'proposed 15–30 seconds' },
  shoutout: { name:'Host shout-out', duration:'proposed 5–10 seconds' },
  board: { name:'Feature board', duration:'proposed 3–5 seconds' }
};
export function placementCopy(company, format) {
  const c=companies[company];
  if(format==='shoutout') return {title:'A quick word from the crew',dialogue:`“A little help for the thing you’re building.” The cast introduces ${c.name} in a short, clearly labeled company moment.`};
  if(format==='board') return {title:'The company between the stories',dialogue:`The next episode is a moment away. ${c.name} gets a dedicated feature board with its name, website, and one useful reason to visit.`};
  return company==='specflow' ? {title:'The idea everyone read differently',dialogue:'“Wait. Are we building the same thing?” SpecFlow gets a role in the crew’s conversation about turning an idea into a shared direction.'} : {title:'The launch meeting',dialogue:'“We have an idea. Now we need a plan.” LaunchPlan gets a natural role in the crew’s next launch.'};
}
export const storyboards = {
  town:[
    {image:'cafe.webp',alt:'Two robot friends at the town cafe.',speaker:'Claude',line:'We have three good launch ideas and one episode slot.'},
    {image:'workshop.webp',alt:'Three robot friends at a crowded workshop.',speaker:'Sage',line:'Then let’s ask the LaunchPlan town which one they want to see.'},
    {image:'cinema.webp',alt:'The crew sitting in front of a company board.',speaker:'Claude',line:'The town picked the idea it wants to see in action.'},
    {image:'town.webp',alt:'The whole miniature town, ready for the next story.',speaker:'Sage',line:'Good. Let’s show the winner working before we celebrate.'}
  ],
  build:[
    {image:'workshop.webp',alt:'Three robots discussing a product at their workbench.',speaker:'Claude',line:'We agreed to build a launch board. Why did we make three different things?'},
    {image:'cafe.webp',alt:'The robot crew talking through the idea at the cafe.',speaker:'Sage',line:'Let’s put one example in SpecFlow: a founder posts a launch, and a reader can find it.'},
    {image:'cinema.webp',alt:'The robot crew presenting the idea on a large board.',speaker:'Blue',line:'Okay. Add a launch, refresh, and there it is. That part works.'},
    {image:'workshop.webp',alt:'The crew returning to their workshop.',speaker:'Claude',line:'Nice. The board can wait; first let’s get someone else to try it.'}
  ]
};
