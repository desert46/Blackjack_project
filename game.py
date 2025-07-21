'''The actual blackjack game'''
import random


def new_deck():
    '''Creates a new deck of cards, shuffles it, and returns the shoe.'''
    # 2s represents 2 of spades, Ah represents Ace of Hearts, etc.
    cards = [
        '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s', 'Ts', 'Js', 'Qs', 'Ks', 'As',
        '2h', '3h', '4h', '5h', '6h', '7h', '8h', '9h', 'Th', 'Jh', 'Qh', 'Kh', 'Ah',
        '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d', 'Td', 'Jd', 'Qd', 'Kd', 'Ad',
        '2c', '3c', '4c', '5c', '6c', '7c', '8c', '9c', 'Tc', 'Jc', 'Qc', 'Kc', 'Ac'
    ]
    _shoe = cards*6  # forms a 6 deck blackjack shoe
    random.shuffle(_shoe)  # shuffle shoe
    return _shoe


def create_card_values():
    '''Returns a dictionary of card values for blackjack.'''
    _card_values = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 10, 'Q': 10, 'K': 10, 'A': 11
    }
    return _card_values


def hand_start(money, bet, shoe, card_values):
    '''Starts the game by dealing two cards to the player and dealer.'''
    natural = False
    player_hand = []
    dealers_hidden_hand = []
    dealers_shown_hand = []
    player_hand_values = []
    dealer_hand_values = []
    # Deal two cards to the player and dealer
    for i in range(2):
        player_hand.append(shoe[0])
        shoe.pop(0)
        dealers_hidden_hand.append(shoe[0])
        dealers_shown_hand.append(shoe[0])
        shoe.pop(0)
    dealers_shown_hand[0] = "Hidden Card"  # hide one of the dealer's cards
    # calculate the initial hand values for the two cards dealt
    for card in player_hand:
        # card[0] takes the rank of the card
        player_hand_values.append(card_values[card[0]])
    for card in dealers_hidden_hand:
        dealer_hand_values.append(card_values[card[0]])
    # Pocket aces scenario
    # Sets one of the aces to 1
    if player_hand_values == [11, 11]:
        player_hand_values = [1, 11]
    if dealer_hand_values == [11, 11]:
        dealer_hand_values = [1, 11]
    # checking for naturals
    if sum(player_hand_values) == 21:
        natural = True
        if sum(dealer_hand_values) == 21:
            print("Both you and the dealer hit a natural")
            print("You get your bet back.")
        else:
            print("You hit a natural!")
            print(f"You won ${bet * 2.5}!")
            money += bet * 2.5
    elif sum(dealer_hand_values) == 21:
        natural = True
        print("Dealer hit a natural!")
        print(f"You lost your bet of ${bet}.")
    return player_hand, dealers_hidden_hand, dealers_shown_hand, player_hand_values, dealer_hand_values, natural


def calculate_hand_value(card_values, hand_values, hand):
    '''Calculates the total value of a hand.'''
    hand_values.append(card_values[hand[-1][0]])
    if sum(hand_values) > 21 and 11 in hand_values:
        # If the hand value is over 21 and contains an Ace, Ace becomes 1
        hand_values[hand_values.index(11)] = 1
    return hand_values, hand


# Start of the game
print("Welcome to Blackjack!")
money = 10000  # Starting money for the player

shoe = new_deck()
card_values = create_card_values()
player_hand_values = []
dealer_hand_values = []

while True:
    if len(shoe) < 100:  # If the shoe has less than 20 cards, reshuffle
        print("Shoe has been reshuffled!")
        shoe = new_deck()
    print(f"You have ${money}")
    bet = input("How much do you want to bet? (or type 'e' to exit): ")
    if bet.isdecimal():
        bet = int(bet)
        if money <= 0:
            print("You have no money left to bet. Game over!")
            break
        if bet > money:
            print(f"You cannot bet more than your current money: ${money}")
            continue
        if bet <= 0:
            print("Bet must be a positive amount.")
            continue
        if bet < 10:
            print("Minimum bet is $10.")
            continue
    elif bet == 'e' or bet == 'E':
        print("The game has ended. Thank you for playing Blackjack!")
        break
    else:
        print("Invalid input. Please enter a valid amount.")
        continue
    money -= bet
    print(f"You have ${money} left.")
    # Start the hand with two cards, capture the returned values
    player_hand, dealers_hidden_hand, dealers_shown_hand, player_hand_values, dealer_hand_values, natural = hand_start(money, bet, shoe, card_values)
    if natural:
        continue  # Skip to the next hand if a natural was hit by either person
    print("\n")
    print(f"Your Hand: {player_hand}")
    print(f"Your Hand Value: {sum(player_hand_values)}")
    print(f"Dealer's Hand: {dealers_shown_hand}")
    # asks player to make a move (hit or stand)
    can_double_down = True
    while True:
        move = input("Do you want to hit or stand or double down? (h/s/d): ").lower()
        if move == 'h':
            # Player chooses to hit
            can_double_down = False
            player_hand.append(shoe[0])
            shoe.pop(0)
            player_hand_values, player_hand = calculate_hand_value(card_values,
                                                                hand=player_hand,
                                                                hand_values=player_hand_values)
            print(f"You drew: {player_hand[-1]}")
            print(f"Your Hand: {player_hand}")
            print(f"Your Hand Value: {sum(player_hand_values)}")
            if sum(player_hand_values) > 21:
                print("You busted")
                print(f"You lost your bet of ${bet}")
                break
        elif move == 's':
            # Player chooses to stand
            print("You chose to stand.")
            print(f"Dealer's Hand was: {dealers_hidden_hand}")
            while sum(dealer_hand_values) < 17:
                dealers_hidden_hand.append(shoe[0])
                shoe.pop(0)
                dealer_hand_values, dealers_hidden_hand = calculate_hand_value(card_values,
                                                                            hand=dealers_hidden_hand,
                                                                            hand_values=dealer_hand_values)
                print(f"Dealer drew: {dealers_hidden_hand[-1]}")
            print(f"Dealer's Hand: {dealers_hidden_hand}")
            print(f"Dealer's Hand Value: {sum(dealer_hand_values)}")
            if sum(dealer_hand_values) > 21:
                print("Dealer went bust. ")
                print(f"You won ${bet * 2}!")
                money += bet * 2
            elif sum(dealer_hand_values) > sum(player_hand_values):
                print("Dealer's hand was higher than yours")
                print(f"You lost your bet of ${bet}")
            elif sum(dealer_hand_values) < sum(player_hand_values):
                print("Your hand was higher than the dealers")
                print(f"You won ${bet * 2}!")
                money += bet * 2
            elif sum(dealer_hand_values) == sum(player_hand_values):
                print("It's a push!")
                print(f"You get your bet of ${bet} back.")
                money += bet
            break
        elif move == 'd':
            # Player chooses to double down
            if can_double_down:
                if bet > money:
                    print("You cannot double down, you do not have enough money.")
                    continue
                print("You chose to double down.")
                money -= bet  # Deduct the bet again for doubling down
                bet *= 2
                player_hand.append(shoe[0])
                shoe.pop(0)
                player_hand_values, player_hand = calculate_hand_value(card_values,
                                                                    hand=player_hand,
                                                                    hand_values=player_hand_values)
                print(f"You drew: {player_hand[-1]}")
                print(f"Your Hand: {player_hand}")
                print(f"Your Hand Value: {sum(player_hand_values)}")
                print(f"Dealer's Hand was: {dealers_hidden_hand}")
                if sum(player_hand_values) > 21:
                    print("You busted")
                    print(f"You lost ${bet}")
                    print(f"Dealers hand was: {dealers_hidden_hand}")
                    break
                while sum(dealer_hand_values) < 17:
                    dealers_hidden_hand.append(shoe[0])
                    shoe.pop(0)
                    dealer_hand_values, dealers_hidden_hand = calculate_hand_value(card_values,
                                                                                   hand=dealers_hidden_hand,
                                                                                   hand_values=dealer_hand_values)
                    print(f"Dealer drew: {dealers_hidden_hand[-1]}")
                print(f"Dealer's Hand: {dealers_hidden_hand}")
                print(f"Dealer's Hand Value: {sum(dealer_hand_values)}")
                if sum(dealer_hand_values) > 21:
                    print("Dealer went bust. ")
                    print(f"You won ${bet}!")
                    money += bet*2
                elif sum(dealer_hand_values) > sum(player_hand_values):
                    print("Dealer's hand was higher than yours")
                    print(f"You lost your bet of ${bet}.")
                elif sum(dealer_hand_values) < sum(player_hand_values):
                    print("Your hand was higher than the dealers")
                    print(f"You won ${bet}!")
                    money += bet*2
                elif sum(player_hand_values) == sum(dealer_hand_values):
                    print("It's a push!")
                    print(f"You get your bet of ${bet} back.")
                    money += bet
            else:
                print("You can only double down on your first move.")
                continue
            break
        else:
            print("Invalid input. Please enter 'h' to hit or 's' to stand.")
    print("End of hand")
    # End of the game
