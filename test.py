def test(a):
    try:
        if a == 1:
            raise Exception
        return a
    except Exception:
        print("error")
    finally:
        print("finally")


if __name__ == "__main__":
    import haruka_bot.plugins.pusher.dynamic_pusher as dynamic
    print(dynamic.get_latest_dynamic(1950658))
