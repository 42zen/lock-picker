# lock-picker


![lock-picker](./images/lock-picker.png)


## Introduction
`lock-picker` is a tool designed to search GitHub repositories for **exposed api keys** from **environment variable**. The tool allows users to customize the search by defining the **minimum or fixed size of API keys**, ensuring that only keys of the desired length are retrieved. Additionally, lock-picker offers an option to **save the collected URLs and keys** to a file for further analysis. This makes it an ideal tool for security researchers, developers, and penetration testers aiming to identify exposed credentials in publicly accessible repositories.


## How to install

You can install **lock-picker** directly from pip:
> pip install lock-picker

Alternatively, you can clone the repository from GitHub:
> git clone https://github.com/42zen/lock-picker


## How to use

To use the tool, simply run:
> lock-picker ENV_VARIABLE
For example, running `lock-picker TWILIO_AUTH_TOKEN` will search for Twilio API keys.

If you installed the tool from the GitHub repository, you can run it with Python:
> python3 lock-picker.py ENV_VARIABLE

To store the results in a text file, use:
> lock-picker ENV_VARIABLE -o api_keys.txt

To capture only API keys of a fixed size (for example, 40 bytes), run:
> lock-picker ENV_VARIABLE -s 40 -u urls.txt

If you want to dump all .env files to a folder, use:
> lock-picker ENV_VARIABLE --dump folder_name


## Credits

- [Mathias Bochet](https://www.linkedin.com/in/mathias-bochet/) (aka [Zen](https://github.com/42zen/)) - Author
- Thanks [Ravi Pousseur](https://medium.com/@ravi.pousseur) for all the fun we had one night working on that a few years ago.
