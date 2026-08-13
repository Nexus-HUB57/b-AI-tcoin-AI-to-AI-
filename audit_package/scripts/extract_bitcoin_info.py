import requests
import csv
import time

# Endereços do arquivo
addresses = [
    "18q8CYvtjdTkrynqjmZaHbHFKMbHB1xqtR",
    "1PmzoeZYGuoUaKYfT2iMzrN4DD9hPUMT4",
    "19RgBq1Un8aGuGbpdWvM4wz9FB6RF28r7R",
    "1CFKG38T6qtd5cQaWmuHyUTTaNRDwEtcru",
    "1PoTRJzMK9ASfVLC2NiWivjStEN2n9yBcu",
    "1KPByWyffoWW8mxVutfLYRezawVu8X4STn",
    "1PRQdYEUGS6NfdZ7Wx7dMKHJFWTsE49dfy",
    "1PzQVyWmL7EndyHUVb7S2AQUhVuhmAq7bU",
    "1H3R49G46jdVmvsYSad3EPpkj3MDGZMKbn",
    "1QBGdrECoqRwHDSTNKtYCc8fHGtPEmMNrb",
    "1Mi4dwPHrHJATZb5QbjknpNWwn9gwtmPeh",
    "1JDqBYr5MxMk6PPSG5h8PUs135fwAYPTti",
    "14PYWowRezYQKozEs7qZQ1N5EvyuzDeWSh",
    "1DNfrhKSnv7J4BFj2jPXedJwHcHqp4SjNZ",
    "1JPJSZVRxVx2S6Qn4dHxhyX5Nwft6afQay",
    "1AZMHaauf1x95y8KEH7faEFacAk6aCG7pm",
    "1MhcKuVTcRea9Snq337CLQQarw865xTTmx",
    "1NUqA6mKWxkxRFw4BzKJbKGa5xYiU6byDU",
    "1FsqLtjp7PFUGuJGcbphzpsPVWJsBFScmB",
    "1LcV3E89XBHJFWgtBJqRXQe9m9ptrM8nuk",
    "1MVnvVoAmkhPiRg5FXew8gWNRWVTLmUKXL",
    "17GQphsE5FVKCL8B6ZVY1XDmPtdT8eXzdK",
    "13Sixtcgp45yasSofupqa2NoxWRLFm8KTJ",
    "1HFBWQj3PWe7m5xrTHVtkKkSunH17RsSro",
    "1A9RCMLrPRrJkPq1errSUhH9x8pXmWUMgv",
    "1Q1d5NkvaEQz9eYTWYcDC6JAQ5QTwwv9Fj",
    "1Ld4Bj1kCAS4gUZVnMHVjYAJSEjH6GuauC",
    "17MQ3FwS2EgxisVWwusfKgGcsxEfL9TLDx",
    "15zQGPvLQS2TY41dJofuihqE24ee6B4nEY",
    "15X9QXRfhms8ozYx6EEnsENCyNN9f2d3Q7",
    "1FNAgWZtjtPBpWGuUM6eQtk5yvBx39zyF4",
    "1LCT7eA39j5DmZAGzv3kKieyJcBRQJnh12",
    "1HHGoXE9616y5jMTTkxNMcbGMaC8nEetVt",
    "1516V8w3MnxUPmioa9QgqSbbVmZuQeBz4E",
    "1KhvWkcouDnSbAcPDKHkekwnC5wn89MeBM",
    "1DpqzoVAV8Ze4L8LjJd92ZcLnmybZjAqQq",
    "17b68QPBXYmtCwMexEzTJxSTbMZRVrfeJW",
    "1HL32rjrH8Mh8J4fgY4t75Htqui1cTeesr",
    "1AQxtrkJM88K6fvV2dDaC2BdUjPYeqUWjc",
    "19upFYCsszQSddK4v72P1furN54ce7uC8i",
    "1KZz3W8z9AsHWyxssPfGEoUUKabjFsaCmi",
    "1JrwodH6MguujtGLP8Gub5RxiFvFvUrKbo",
    "1Le99my24Zj8ePBXPdWwAEHEUwG4nhkH3w",
    "1HzSQSjLVX9GDyyd8m6eQQB4RsqtJyQGpx",
    "1LbqPqwavkbVJ2HS9QR5W2Hg18ADvW5pDq",
    "1DBkCw3PZxrdHm5YDhMDJ4WAnco4omYQa4",
    "1KeKsN8gP8jrnN5coGJ2aMevX2fcMJDTrQ",
    "1M43Kmn4fMYTd5bnBQ3moBPRQRkinCVk4R",
    "1EQYYANSUQCxnj955uPMtLanwBvrfFJFRV",
    "1Jx9hxfXTrF3ZAWQb45PUmBh2NL1QRHU3o",
    "1E8orpLTpZUTngAj7QfEm7X2VH7BWDKXoD"
]

# Mapear chaves privadas
private_keys = {
    "18q8CYvtjdTkrynqjmZaHbHFKMbHB1xqtR": "p2pkh:KyipHsDLJgauAacmRyTDvC1Ac8oa6qbqqDrwSJfhEZkhtxHBnwxF",
    "1PmzoeZYGuoUaKYfT2iMzrN4DD9hPUMT4": "p2pkh:KwZMqrMSo5TSaSQ6mT4SXpsb5eLq9jUNf8aadmg8pp3U4q8y5owx",
    "19RgBq1Un8aGuGbpdWvM4wz9FB6RF28r7R": "p2pkh:KzSpyD8AdE3LnoeXJQz1mVkVRahfKhC23P4DDGQDwT236RnHSJKK",
    "1CFKG38T6qtd5cQaWmuHyUTTaNRDwEtcru": "p2pkh:L3qm3ajAFuJp723inRYWW33cJYakr3X8a9NE8i6CJF1vQKnP6EUt",
    "1PoTRJzMK9ASfVLC2NiWivjStEN2n9yBcu": "p2pkh:L3QtHArFWoBmnariXEKA6onmbNxeckUUncRKnJZ87RAnyCgb5Ash",
    "1KPByWyffoWW8mxVutfLYRezawVu8X4STn": "p2pkh:KzXCXuNZhXvvW1oHsgCcjCEagf9qdX7xr4icyu4HAyCHyqxq5okN",
    "1PRQdYEUGS6NfdZ7Wx7dMKHJFWTsE49dfy": "p2pkh:L3UYaoPCHxVHG4UNNdniBARu6hZ5cqruzfarPAauKeeAChpen1Fs",
    "1PzQVyWmL7EndyHUVb7S2AQUhVuhmAq7bU": "p2pkh:KyxK77oZNifdfKKDCnJQNC33w1ZsEaST8A2DN7AZ67s1nrZmeMSP",
    "1H3R49G46jdVmvsYSad3EPpkj3MDGZMKbn": "p2pkh:KyfMwQKZTHiduC2Sa72gk6CtdZUx9TgT8RQvxmKfeFYjN3CZPt8P",
    "1QBGdrECoqRwHDSTNKtYCc8fHGtPEmMNrb": "p2pkh:L2PKbe5dREzmHC9ZuxhKWaiRbicLiadboHvxYNCwFPQudGDS2CMH",
    "1Mi4dwPHrHJATZb5QbjknpNWwn9gwtmPeh": "p2pkh:L5G3cHUXnUzsCWyZrgvGvQRz5tciWKyDh45vHvRntquNUSQTbW1M",
    "1JDqBYr5MxMk6PPSG5h8PUs135fwAYPTti": "p2pkh:L5gXgZ2XzfBNR3YDzyFTeKMNRHPc3oR6dsvrQzsG7mszU2JRpVnH",
    "14PYWowRezYQKozEs7qZQ1N5EvyuzDeWSh": "p2pkh:L424f8jFXmHN4NN2rHmDZAFVTym1kupdyx9BztHrcEL3Foj9gKgN",
    "1DNfrhKSnv7J4BFj2jPXedJwHcHqp4SjNZ": "p2pkh:Kwe8HB1BnhC1vibfZ4pXxDbshBZ7cyTntRnGCD843EmSNDsY5J1Q",
    "1JPJSZVRxVx2S6Qn4dHxhyX5Nwft6afQay": "p2pkh:L1pcZ62FNi7Fs5bpZkuRR2m7wFqM1bHCuFEsadbuhynGjcBSZqme",
    "1AZMHaauf1x95y8KEH7faEFacAk6aCG7pm": "p2pkh:L5hQeeYUj4Fo1ahB1fTxWMYhcuo1iNSBebRisivxjdw5efXRfx7V",
    "1MhcKuVTcRea9Snq337CLQQarw865xTTmx": "p2pkh:KzJCQiyrg6pf9M2PUgiYZuLmQJHp1XovMrHCAQJXSWPbYQRUcJvW",
    "1NUqA6mKWxkxRFw4BzKJbKGa5xYiU6byDU": "p2pkh:KzgbbxaHDEFaMvuUYqtNr1HCDzRyHSkaK4iida9j4zCjpBt9Lwo3",
    "1FsqLtjp7PFUGuJGcbphzpsPVWJsBFScmB": "p2pkh:L4LS6KWrzik3DwYFrmS4prvPpmY4ikkpPFdvGbb9dca2J3u3X5Me",
    "1LcV3E89XBHJFWgtBJqRXQe9m9ptrM8nuk": "p2pkh:L2stChQSHjMQhzoCWdzAsCE2gGZNDTXJpgdRWqBw16HXjdX5QUyF",
    "1MVnvVoAmkhPiRg5FXew8gWNRWVTLmUKXL": "p2pkh:KwgA8mLVy8VhoYPPC2p21tr2pAF1LFEHbfj8HUawx4h5EHqUH9Jc",
    "17GQphsE5FVKCL8B6ZVY1XDmPtdT8eXzdK": "p2pkh:L3knLHTVJ3aDdnrmarMfpXjaXCtvET8CxmtoCkxfBzjaSCLd6sQx",
    "13Sixtcgp45yasSofupqa2NoxWRLFm8KTJ": "p2pkh:L1XXGZGyPq5EFTbBZEuR4JKnr8VbDz1Jw86bMTTbERCa7NnLFEsq",
    "1HFBWQj3PWe7m5xrTHVtkKkSunH17RsSro": "p2pkh:L2UtWb49V9ti2dZAVHMy8NHe5bon7U7ZfUynLR5Hd74YHXWPoKD7",
    "1A9RCMLrPRrJkPq1errSUhH9x8pXmWUMgv": "p2pkh:L1YYyj4KaWFbeJqvbDuvNxcMedELLJ7GEC1zEMq1s4DYTkvQbJud",
    "1Q1d5NkvaEQz9eYTWYcDC6JAQ5QTwwv9Fj": "p2pkh:L5nXn2UKLHSSyGoXqaJaBh1LaTK8WiqFr3G1H8paC3CGGFtLzMJC",
    "1Ld4Bj1kCAS4gUZVnMHVjYAJSEjH6GuauC": "p2pkh:KyFUfaWMcqAvgn9zQAqtFSdyE1ksQfKfL3mnUHwsd19EDwHP7NoH",
    "17MQ3FwS2EgxisVWwusfKgGcsxEfL9TLDx": "p2pkh:L4u6KWS5s4TneAwn7rUc8Lkcfs25g7QSqPYGvwSjKix9nAGZu9rX",
    "15zQGPvLQS2TY41dJofuihqE24ee6B4nEY": "p2pkh:L4iEZBGsS6tDGkCipKvvWrKHLgdDTrE8oVoBy5uG7EGtQ6WzbDgq",
    "15X9QXRfhms8ozYx6EEnsENCyNN9f2d3Q7": "p2pkh:L56LotEmuwEDVnP4BsDhYk9Ne9qDMkHAWC6JaDLX86yxapGGFxoq",
    "1FNAgWZtjtPBpWGuUM6eQtk5yvBx39zyF4": "p2pkh:L4srqwMWRZCsb97es5sJ2GkUo1igVisrtcTTWk1Mj3NWWefVkBoc",
    "1LCT7eA39j5DmZAGzv3kKieyJcBRQJnh12": "p2pkh:L1bC5dwXARpuU7U1EQobDeE4hLCtQAsbq6ANkcTUPYFMwtjK3EMJ",
    "1HHGoXE9616y5jMTTkxNMcbGMaC8nEetVt": "p2pkh:L24kC7cf51FEc6qejnjyDCCGRAhzFiyansjpRu1Dz1QnVbjWnYNA",
    "1516V8w3MnxUPmioa9QgqSbbVmZuQeBz4E": "p2pkh:L5nj7A3TaiEguuRHMpqqUqRsYBF6fZJsuXkSp1qD7s6vNedTxHTz",
    "1KhvWkcouDnSbAcPDKHkekwnC5wn89MeBM": "p2pkh:L42zZ5mkkf2q412gRtkJ8yPzfJvHEuWDmDHDFmW6xrhXZxvyDutM",
    "1DpqzoVAV8Ze4L8LjJd92ZcLnmybZjAqQq": "p2pkh:KyHvWBwmVCaEqyx2Ups7msYskQH6GVJswB1hSx6pTHndFmnEaYE4",
    "17b68QPBXYmtCwMexEzTJxSTbMZRVrfeJW": "p2pkh:Kwm9aC6aiM5Q1MoQxbKjy9dSct5QG7PbypjkMHzobWBEiwzo4fcs",
    "1HL32rjrH8Mh8J4fgY4t75Htqui1cTeesr": "p2pkh:KzcFA8y4WnNhD1AZKrSAy4Q8DMthoKvZFREN2EM4Yd55HHp7ZXXC",
    "1AQxtrkJM88K6fvV2dDaC2BdUjPYeqUWjc": "p2pkh:KzgXoq6YuS4otvTnjsxfZAxnN2RZcZRbxbphFJoKcgvhK1gRoNW4",
    "19upFYCsszQSddK4v72P1furN54ce7uC8i": "p2pkh:Ky9bzLmuFxSj4STAJfhAFNENebyj8UnXgrt66hzTnz4yahae177g",
    "1KZz3W8z9AsHWyxssPfGEoUUKabjFsaCmi": "p2pkh:L3iAq9eS5aSFHHqnC3XoubVuusL5AHP6e8nVmGbuBTK3jaFsP5ud",
    "1JrwodH6MguujtGLP8Gub5RxiFvFvUrKbo": "p2pkh:KyBCLpMG7mETpHapvhoyPdNFjbs5Ruf2uPJk9cW5N5ATizuKMc9c",
    "1Le99my24Zj8ePBXPdWwAEHEUwG4nhkH3w": "p2pkh:KzbAPZ9eKkKCccAhfdceMYLnrV6EpjgwRygm14KkDMaDwiU61GnP",
    "1HzSQSjLVX9GDyyd8m6eQQB4RsqtJyQGpx": "p2pkh:L5hxkFExYtUdgJ4gwMjTXo6s73a7qFVM1iyJqRHygktMkKHtzAH8",
    "1LbqPqwavkbVJ2HS9QR5W2Hg18ADvW5pDq": "p2pkh:L1eBxMPxBNmkpFuE3674dJ9AqsvpqJ6FC7AhjFpRHRzEeApDYNS7",
    "1DBkCw3PZxrdHm5YDhMDJ4WAnco4omYQa4": "p2pkh:Kyp2mPdX94qZVkpMRGjKLQE6mifyjSGN3Z3NGJ3UBQHAJo2tLkHq",
    "1KeKsN8gP8jrnN5coGJ2aMevX2fcMJDTrQ": "p2pkh:KyUvRPZLU7Ufov1741KaLjT5UCgYhnCsnM5xyr2DHQWfXhUR9sj1",
    "1M43Kmn4fMYTd5bnBQ3moBPRQRkinCVk4R": "p2pkh:Ky7Xu8uiyXceDTJV7zdsjxKsrKDrvyVmZBUbKk7MRYWtRaRLo1v6",
    "1EQYYANSUQCxnj955uPMtLanwBvrfFJFRV": "p2pkh:L37HCDzTH7uHfSeT1K7wcMQ3MZkyPcfLE6e9MiQF3KdZoBqU5kVQ",
    "1Jx9hxfXTrF3ZAWQb45PUmBh2NL1QRHU3o": "p2pkh:L194E5NzCEeETeWHK1iBCofdHXD5G1G8cyJkvfMsHafbi9VAo3L2",
    "1E8orpLTpZUTngAj7QfEm7X2VH7BWDKXoD": "p2pkh:KydKB6MnKnGtpT5KNosq72dYZHSmQbgA7Tkr3eAhwMnDAb6br68R"
}

# Função para consultar saldo
def get_balance(address):
    url = f"https://blockstream.info/api/address/{address}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            funded = data["chain_stats"]["funded_txo_sum"]
            spent = data["chain_stats"]["spent_txo_sum"]
            balance = funded - spent
            return balance
        else:
            return "Erro"
    except Exception as e:
        return f"Erro: {str(e)}"

# Consultar saldos e criar arquivo
print("Consultando saldos na blockchain...")
with open("electrum-private-keys-with-balance.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["address", "private_key", "balance_satoshi"])
    
    for i, address in enumerate(addresses):
        balance = get_balance(address)
        private_key = private_keys.get(address, "Chave não encontrada")
        writer.writerow([address, private_key, balance])
        
        print(f"{i+1}/50 - {address}: {balance} satoshis")
        time.sleep(0.5)  # Respeitar rate limit

print("✅ Processo concluído!")
print("Arquivo \'electrum-private-keys-with-balance.csv\' gerado com sucesso!")

