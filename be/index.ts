const express = require('express');
const app = express();
const port = process.env.PORT || 4000;

app.get('/', (req: import('express').Request, res: import('express').Response) => {
  res.send('Hello from Express + TypeScript!');
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
