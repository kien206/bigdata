import logging
from XCrawler import XCrawler
from exceptions.exceptions import *
import time
queries = [
    'Web3',
    'Decentralized Web',
    'Blockchain',
    'Smart Contract',
    'DApp',
    'DeFi',
    'NFT',
    'Ethereum',
    'Polkadot',
    'Solana',
    'Cardano',
    'Tezos',
    'Solidity',
    'Smart Contract Development',
    'Web3.js',
    'Ethers.js',
    'Rust',
    'SmartPy',
    'Cryptocurrency',
    'Tokenomic',
    'Consensus Algorithm',
    'Decentralization',
    'Wallets',
    'MetaMask',
    'Uniswap',
    'Aave',
    'Chainlink',
    'OpenSea',
    'Blockchain Meetups',
    'Web3 Conferences',
    'Crypto Communities'
]
test = ['NFT', 'ethereum']
def main():
    for query in queries:
        start = time.time()
        twitter_getter = XCrawler(username='kien20603', 
                            password='Kien.lt20214907', 
                            email_address='kien.lt0620@gmail.com', 
                            query=query, 
                            num_scrolls=100, 
                            mode=1, 
                            wait_scroll_base = 2, 
                            wait_scroll_epsilon = 1,
                            since_time='2023-01-01',
                            until_time='2023-11-13')
        try:
            twitter_getter.login()
        except ElementNotLoaded as e:
            raise e

        print("Setting query in the object")
        print("Start Search, this will input the query and perform the scroll with the selected mode")
        try:
            twitter_getter.search()
        except ElementNotLoaded as e:
            raise e
        except NoTweetsReturned as e:
            print(e)

        print("Printing returned results and going home")
        try:
            twitter_getter.print_results()
        except UnicodeEncodeError:
            continue
        twitter_getter.save_to_json()
        twitter_getter.go_home()
        print("Clearing Results")
        twitter_getter.clear_tweets()
        print("quitting browser")
        twitter_getter.quit_browser()
        print(start - time.time())
    twitter_getter.save_to_csv('twitter_2023.csv')

if __name__=='__main__':
    main()