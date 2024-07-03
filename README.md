# WordPress Multi-Site Management System

This application is a comprehensive solution for managing multiple WordPress sites, including deployment via Simply Static Pro.

## Features

- **Domain Management**: Add new domains or install WordPress on existing domains
- **WordPress Installation**: Automated WordPress setup with required plugins
- **Article Editor**: Built-in TinyMCE editor for writing and publishing articles across multiple sites
- **Site Monitoring**: Dashboard to monitor site status, published articles, and indexed articles
- **Static Site Deployment**: Nightly deployment of static sites to GitHub Pages using Simply Static Pro
- **SEO Monitoring**: Integration with SpaceSERP API for tracking indexed articles

## Key Components

1. **Domain Addition**: Interface for adding new domains and triggering WordPress installation
2. **WordPress Management**: Automated installation and configuration of WordPress sites
3. **Content Editor**: TinyMCE-based editor for multi-site article publishing
4. **Monitoring Dashboard**: Overview of all managed sites with key metrics
5. **Automated Deployment**: Nightly static site generation and deployment to GitHub Pages

## Technical Stack

- Backend: Python
- Frontend: HTML, CSS, JavaScript
- Static Site Generator: Simply Static Pro
- Deployment: GitHub Pages
- Domain Management: InternetBS API
- SEO Tracking: SpaceSERP API

## Getting Started

To get started with this project, follow these steps:

1. Clone the repository from GitHub:
   ```bash
   git clone https://github.com/eldertek/wp-deploy
   ```

2. Navigate to the project directory:
   ```bash
   cd wp-deploy
   ```

3. Run the application:
   ```bash
   python run.py
   ```

That's it! The application should now be up and running.

## Usage

You can log in to the web interface using the default credentials:
- **Username**: admin
- **Password**: adminpass

Once logged in, you can manage domains, install WordPress, edit articles, monitor site status, and deploy static sites.

## Contributing

We welcome contributions to the project! Please feel free to open pull requests and issues.
