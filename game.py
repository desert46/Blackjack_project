'''The actual blackjack game'''
import random


def new_deck():
    cards = [
        '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s', 'Ts', 'Js', 'Qs', 'Ks', 'As',
        '2h', '3h', '4h', '5h', '6h', '7h', '8h', '9h', 'Th', 'Jh', 'Qh', 'Kh', 'Ah',
        '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d', 'Td', 'Jd', 'Qd', 'Kd', 'Ad',
        '2c', '3c', '4c', '5c', '6c', '7c', '8c', '9c', 'Tc', 'Jc', 'Qc', 'Kc', 'Ac'
    ]
    _shoe = cards*6  # forms a 6 deck blackjack shoe
    random.shuffle(_shoe)  # shuffle shoe
    return _shoe


def hand_start(_shoe):
    player_hand = []
    dealer_hand = []
    print(_shoe)
    for i in range(2):
        player_hand.append(_shoe[0])
        shoe.pop(0)
        dealer_hand.append(_shoe[0])
        shoe.pop(0)

    print("Your Hand")
    print(player_hand)
    print("Dealers Hand")
    print(dealer_hand)


shoe = new_deck()
hand_start(shoe)
