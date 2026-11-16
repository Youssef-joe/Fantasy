#!/usr/bin/env node

const { Command } = require('commander');
const { exec } = require('child_process');
const ora = require('ora');
const chalk = require('chalk');

const logo = chalk.blue.bold(`
  ███████╗ █████╗ ███╗   ██╗████████╗ █████╗ ███████╗██╗   ██╗
  ██╔════╝██╔══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔════╝╚██╗ ██╔╝
  █████╗  ███████║██╔██╗ ██║   ██║   ███████║███████╗ ╚████╔╝
  ██╔══╝  ██╔══██║██║╚██╗██║   ██║   ██╔══██║╚════██║  ╚██╔╝
  ██║     ██║  ██║██║ ╚████║   ██║   ██║  ██║███████║   ██║
  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚══════╝   ╚═╝
             Football Prediction System
`);

console.log(logo);

const program = new Command();

program
  .name('fantasy-cli')
  .description('CLI for Fantasy Football Prediction System')
  .version('1.0.0');

program.command('scrape')
  .description('Scrape fresh data from FPL API')
  .action(() => {
    const spinner = ora(chalk.cyan('Scraping data from FPL API...')).start();
    exec('python scraper/main.py', (error, stdout, stderr) => {
      if (error) {
        spinner.fail(chalk.red(`Scraping failed: ${error.message}`));
        return;
      }
      spinner.succeed(chalk.green('Data scraped successfully'));
      console.log(stdout);
      if (stderr) console.error(stderr);
    });
  });

program.command('etl')
  .description('Load and process data into database')
  .action(() => {
    const spinner = ora(chalk.magenta('Running ETL pipeline...')).start();
    exec('python -m backend.etl', (error, stdout, stderr) => {
      if (error) {
        spinner.fail(chalk.red(`ETL failed: ${error.message}`));
        return;
      }
      spinner.succeed(chalk.green('ETL completed successfully'));
      console.log(stdout);
      if (stderr) console.error(stderr);
    });
  });

program.command('features')
  .description('Calculate features')
  .action(() => {
    const spinner = ora(chalk.yellow('Calculating features...')).start();
    exec('python -m backend.features', (error, stdout, stderr) => {
      if (error) {
        spinner.fail(chalk.red(`Feature calculation failed: ${error.message}`));
        return;
      }
      spinner.succeed(chalk.green('Features calculated successfully'));
      console.log(stdout);
      if (stderr) console.error(stderr);
    });
  });

program.command('train')
  .description('Train the ML model')
  .action(() => {
    const spinner = ora(chalk.blue('Training ML model...')).start();
    exec('python ml/train.py', (error, stdout, stderr) => {
      if (error) {
        spinner.fail(chalk.red(`Training failed: ${error.message}`));
        return;
      }
      spinner.succeed(chalk.green('Model trained successfully'));
      console.log(stdout);
      if (stderr) console.error(stderr);
    });
  });

program.command('predict')
  .description('Generate predictions')
  .option('-g, --gameweek <number>', 'Gameweek number', 37)
  .option('-t, --top <number>', 'Top N players', 20)
  .option('-i, --show-injured', 'Show injured players')
  .action((options) => {
    const spinner = ora(chalk.cyan(`Generating predictions for GW${options.gameweek}, top ${options.top}...`)).start();
    let cmd = `python ml/predict.py --gameweek ${options.gameweek} --top ${options.top}`;
    if (options.showInjured) cmd += ' --show-injured';
    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        spinner.fail(chalk.red(`Prediction failed: ${error.message}`));
        return;
      }
      spinner.succeed(chalk.green('Predictions generated successfully'));
      console.log(stdout);
      if (stderr) console.error(stderr);
    });
  });

program.command('export')
  .description('Export predictions to the static JSON feed in frontend/data/predictions')
  .requiredOption('-g, --gameweek <number>', 'Gameweek number')
  .action((options) => {
    const spinner = ora(chalk.cyan(`Exporting predictions for GW${options.gameweek}...`)).start();
    const cmd = `python ml/export_predictions.py ${parseInt(options.gameweek, 10)}`;
    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        spinner.fail(chalk.red(`Export failed: ${error.message}`));
        if (stderr) console.error(stderr);
        process.exitCode = 1;
        return;
      }
      spinner.succeed(chalk.green('Predictions exported'));
      console.log(stdout);
    });
  });

program.command('serve')
  .description('Serve the frontend locally at http://localhost:3000')
  .action(() => {
    console.log(chalk.yellow('Serving frontend/ at http://localhost:3000 (Ctrl+C to stop)'));
    const child = require('child_process').spawn('python', ['-m', 'http.server', '3000', '--directory', 'frontend'], { stdio: 'inherit' });
    child.on('error', (error) => {
      console.error(chalk.red(`Failed to start server: ${error.message}`));
    });
  });

program.parse();